"""
原始记录校核引擎

对已转换或已导入的检测数据进行多维度校核：
  1. 异常值识别 — OCR噪声、非法文本值
  2. 数值合理性 — 标准限值比对、物理范围校验、空白样校验
  3. 关联一致性 — 总硬度/钙镁、三卤甲烷等指标间交叉验证
  4. 元信息校核 — 被检单位/水厂/日期合理性
  5. 精度与格式 — 检出限格式、有效位数一致性

输入格式（与 raw_data_converter 输出兼容）:
  samples: [{'样品编号': ..., '被检单位': ..., '被检水厂': ..., '样品类型': ..., '采样日期': ...}, ...]
  data:    {sample_id: {param_name: value_str, ...}, ...}

输出格式:
  [{'level': 'error'|'warning'|'notice',
    'category': '异常值'|'数值合理性'|'关联一致性'|'元信息'|'精度与格式',
    'sample': '样品编号',
    'indicator': '指标名（可选）',
    'message': '描述'}, ...]
"""

import re
import sqlite3
from datetime import datetime, date

DATABASE_PATH = 'database/water_quality_v2.db'

# ── 检出限与数值解析 ─────────────────────────────────────────────────────

# 合法检出限格式: <0.010, <0.002, ＜0.05 等
DETECTION_LIMIT_RE = re.compile(r'^[<＜]\s*(\d+\.?\d*)$')

# 纯数值（含负号、科学计数法）
NUMERIC_RE = re.compile(r'^-?\d+\.?\d*(?:[eE][+-]?\d+)?$')


def parse_numeric(val_str):
    """尝试将字符串解析为数值。返回 (float, is_limit)，解析失败返回 (None, False)"""
    if val_str is None:
        return None, False
    s = str(val_str).strip()
    # 检出限
    m = DETECTION_LIMIT_RE.match(s)
    if m:
        return float(m.group(1)), True
    # 普通数值
    if NUMERIC_RE.match(s):
        return float(s), False
    return None, False


def is_text_indicator(name):
    """判断是否为文本型指标（不应做数值校验）"""
    text_indicators = {'肉眼可见物', '臭和味'}
    return name in text_indicators


# 页眉/页脚/签名区域关键词，被转换器误采为指标时应跳过
_NOISE_KEYWORDS = [
    '制表', '审核', '制 表', '审 核', 'Form', 'form', '日期',
    '第', '页', '共', '国家城市供水', '监测站', '汇总表',
    '分析结果', '检测结果', '防', '张系', '林SJL', 'NO:',
]


def is_noise_indicator(name):
    """判断是否为页眉页脚等噪声（非真实检测指标）"""
    if not name:
        return True
    return any(kw in name for kw in _NOISE_KEYWORDS)


# ── 标准限值解析 ─────────────────────────────────────────────────────────

def parse_limit_value(limit_str):
    """
    从数据库 limit_value 字段解析数值上限。
    支持格式: '0.3', '≤1.0(II类)', '0.05-2', '15', '100', '不应检出'
    返回 (lower_bound, upper_bound) 或 None
    """
    if not limit_str:
        return None
    s = str(limit_str).strip()

    # 跳过过长的描述性文本（如水温的限值说明）
    if len(s) > 30 or '\n' in s:
        return None

    # "不应检出" / "不得检出"
    if '不' in s and '检出' in s:
        return (0, 0)

    # 范围格式: "0.05-2", "6～9", "6.5~8.5"
    m = re.match(r'^(\d+\.?\d*)\s*[-～~]\s*(\d+\.?\d*)$', s)
    if m:
        return (float(m.group(1)), float(m.group(2)))

    # "≤1.0(II类)" 或 "≤0.05(II类)"
    m = re.match(r'^[≤<＜]\s*(\d+\.?\d*)(?:\(.*\))?$', s)
    if m:
        return (None, float(m.group(1)))

    # "≥6(II类)"
    m = re.match(r'^[≥>＞]\s*(\d+\.?\d*)(?:\(.*\))?$', s)
    if m:
        return (float(m.group(1)), None)

    # 纯数值: "15", "100", "0.3"
    if NUMERIC_RE.match(s):
        return (None, float(s))

    return None


# ── 已知 OCR 噪声模式 ────────────────────────────────────────────────────

# 单个无意义汉字/符号（常见 OCR 残留）
OCR_NOISE_RE = re.compile(r'^[去才大—△##＃※◇○●□■☆★\s]{1,3}$')


# ── 校核引擎 ─────────────────────────────────────────────────────────────

class RawDataValidator:
    """原始记录校核引擎"""

    def __init__(self, db_path=None):
        self.db_path = db_path or DATABASE_PATH
        self._limit_cache = None

    def _get_limits(self):
        """从数据库加载指标限值，缓存结果"""
        if self._limit_cache is not None:
            return self._limit_cache

        limits = {}
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute(
                "SELECT name, unit, limit_value FROM indicators "
                "WHERE limit_value IS NOT NULL AND limit_value != ''"
            ).fetchall()
            conn.close()
            for name, unit, lv in rows:
                parsed = parse_limit_value(lv)
                if parsed is not None:
                    limits[name] = {'bounds': parsed, 'unit': unit, 'raw': lv}
        except Exception:
            pass

        self._limit_cache = limits
        return limits

    def _get_known_companies(self):
        """获取系统中已有的被检单位（从 raw_data_records 和 companies 表汇总）"""
        names = set()
        try:
            conn = sqlite3.connect(self.db_path)
            for row in conn.execute(
                "SELECT DISTINCT company_name FROM raw_data_records "
                "WHERE company_name IS NOT NULL AND company_name != ''"
            ):
                names.add(row[0])
            for row in conn.execute("SELECT name FROM companies"):
                names.add(row[0])
            for row in conn.execute(
                "SELECT DISTINCT inspected_unit FROM customers "
                "WHERE inspected_unit IS NOT NULL AND inspected_unit != ''"
            ):
                names.add(row[0])
            conn.close()
        except Exception:
            pass
        return names

    def _get_known_plants(self):
        """获取系统中已有的被检水厂"""
        names = set()
        try:
            conn = sqlite3.connect(self.db_path)
            for row in conn.execute(
                "SELECT DISTINCT plant_name FROM raw_data_records "
                "WHERE plant_name IS NOT NULL AND plant_name != ''"
            ):
                names.add(row[0])
            for row in conn.execute("SELECT plant_name FROM plants"):
                names.add(row[0])
            for row in conn.execute(
                "SELECT DISTINCT water_plant FROM customers "
                "WHERE water_plant IS NOT NULL AND water_plant != ''"
            ):
                names.add(row[0])
            conn.close()
        except Exception:
            pass
        return names

    # ── 主入口 ────────────────────────────────────────────────────────

    def validate(self, samples, data, detection_date=None):
        """
        对样品数据执行全量校核。

        参数:
            samples: 样品元信息列表
            data: {sample_id: {param: value_str}}
            detection_date: 检测日期字符串(YYYY-MM-DD)，可选

        返回: 校核结果列表
        """
        results = []
        results.extend(self._check_anomalies(samples, data))
        results.extend(self._check_plausibility(samples, data))
        results.extend(self._check_consistency(samples, data))
        results.extend(self._check_metadata(samples, detection_date))
        results.extend(self._check_precision(samples, data))
        return results

    def validate_from_db(self, sample_numbers, detection_date=None):
        """
        从数据库加载数据并校核（供方案A的Tab使用）。

        参数:
            sample_numbers: 样品编号列表
            detection_date: 检测日期字符串(YYYY-MM-DD)，可选

        返回: 校核结果列表
        """
        samples = []
        data = {}
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            for sn in sample_numbers:
                rec = conn.execute(
                    "SELECT * FROM raw_data_records WHERE sample_number = ?", (sn,)
                ).fetchone()
                if not rec:
                    continue
                samples.append({
                    '样品编号': rec['sample_number'],
                    '被检单位': rec['company_name'] or '',
                    '被检水厂': rec['plant_name'] or '',
                    '样品类型': rec['sample_type'] or '',
                    '采样日期': rec['sampling_date'] or '',
                })
                vals = conn.execute(
                    "SELECT column_name, value FROM raw_data_values WHERE record_id = ?",
                    (rec['id'],)
                ).fetchall()
                data[sn] = {v['column_name']: v['value'] for v in vals}
            conn.close()
        except Exception:
            pass

        return self.validate(samples, data, detection_date)

    # ── 1. 异常值识别 ─────────────────────────────────────────────────

    def _check_anomalies(self, samples, data):
        results = []
        for s in samples:
            sid = s['样品编号']
            params = data.get(sid, {})
            for param, val in params.items():
                if val is None:
                    continue
                val_str = str(val).strip()
                if not val_str:
                    continue

                # 文本型指标或页眉页脚噪声跳过
                if is_text_indicator(param) or is_noise_indicator(param):
                    continue

                # OCR 噪声检测
                if OCR_NOISE_RE.match(val_str):
                    results.append({
                        'level': 'error',
                        'category': '异常值',
                        'sample': sid,
                        'indicator': param,
                        'message': f'值 "{val_str}" 疑似OCR识别错误',
                    })
                    continue

                # 数值型指标应为数值或检出限格式
                num, is_limit = parse_numeric(val_str)
                if num is None:
                    # 非数值、非检出限、非已知文本 → 异常
                    results.append({
                        'level': 'warning',
                        'category': '异常值',
                        'sample': sid,
                        'indicator': param,
                        'message': f'值 "{val_str}" 不是有效的数值或检出限格式',
                    })

        return results

    # ── 2. 数值合理性 ─────────────────────────────────────────────────

    def _check_plausibility(self, samples, data):
        results = []
        limits = self._get_limits()

        # 基本物理范围
        physical_ranges = {
            'pH': (1, 14),
            '水温': (-5, 60),
            '电导率': (0, 10000),
        }

        for s in samples:
            sid = s['样品编号']
            sample_type = s.get('样品类型', '')
            is_blank = sid.startswith('K')
            params = data.get(sid, {})

            for param, val in params.items():
                val_str = str(val).strip() if val is not None else ''
                if not val_str or is_text_indicator(param) or is_noise_indicator(param):
                    continue

                num, is_limit = parse_numeric(val_str)
                if num is None:
                    continue  # 非数值已在异常值检查中处理

                if is_limit:
                    continue  # 检出限值不做超标判断

                # 物理范围检查
                for key, (lo, hi) in physical_ranges.items():
                    if key in param:
                        if num < lo or num > hi:
                            results.append({
                                'level': 'error',
                                'category': '数值合理性',
                                'sample': sid,
                                'indicator': param,
                                'message': f'值 {val_str} 超出物理范围 {lo}~{hi}',
                            })
                        break

                # 标准限值比对（模糊匹配指标名）
                limit_info = self._match_limit(param, limits)
                if limit_info:
                    bounds = limit_info['bounds']
                    lo, hi = bounds
                    exceeded = False
                    if lo is not None and hi is not None:
                        # 范围型 (如 pH 6.5~8.5)
                        if num < lo or num > hi:
                            exceeded = True
                    elif hi is not None:
                        # 上限型 (如 铝 ≤0.2)
                        if lo == 0 and hi == 0:
                            # 不应检出
                            if num > 0:
                                exceeded = True
                        elif num > hi:
                            exceeded = True
                    elif lo is not None:
                        # 下限型 (如 溶解氧 ≥6)
                        if num < lo:
                            exceeded = True

                    if exceeded:
                        results.append({
                            'level': 'warning',
                            'category': '数值合理性',
                            'sample': sid,
                            'indicator': param,
                            'message': f'值 {val_str} 超过标准限值 ({limit_info["raw"]})',
                        })

                # 空白样检查：数值型指标应为未检出或极低
                if is_blank and not is_limit and num > 0:
                    # 对空白样，若检出了明显数值，给出提示
                    if limit_info and limit_info['bounds'][1] is not None:
                        upper = limit_info['bounds'][1]
                        if upper > 0 and num > upper * 0.1:
                            results.append({
                                'level': 'warning',
                                'category': '数值合理性',
                                'sample': sid,
                                'indicator': param,
                                'message': f'空白样检出值 {val_str}，超过限值10%',
                            })

        return results

    def _match_limit(self, param_name, limits):
        """模糊匹配指标名到限值表"""
        # 精确匹配
        if param_name in limits:
            return limits[param_name]

        # 去掉单位括号后匹配: "氟化物(mg/L)" → "氟化物"
        base = re.sub(r'\([^)]*\)$', '', param_name).strip()
        if base in limits:
            return limits[base]

        # 已知别名映射
        aliases = {
            '六价铬': '铬(六价)',
            '挥发酚': '挥发酚类(以苯酚计)',
            '总α': '总α放射性',
            '总β': '总β放射性',
            '化学需氧量': '化学需氧量(COD)',
            '五日生化需氧量': '五日生化需氧量(BOD5)',
            '总硬度': '总硬度(以CaCO3计)',
            '氨氮': '氨(以N计)',
        }
        # 从 param_name 中提取基础名用于别名查找
        for alias, canonical in aliases.items():
            if alias in param_name and canonical in limits:
                return limits[canonical]

        return None

    # ── 3. 关联一致性 ─────────────────────────────────────────────────

    def _check_consistency(self, samples, data):
        results = []
        for s in samples:
            sid = s['样品编号']
            params = data.get(sid, {})

            results.extend(self._check_hardness_consistency(sid, params))
            results.extend(self._check_thm_consistency(sid, params))

        # 同一水厂出厂水与管网水对比
        results.extend(self._check_plant_consistency(samples, data))

        return results

    def _check_hardness_consistency(self, sid, params):
        """总硬度 ≈ Ca × 2.497 + Mg × 4.118"""
        results = []

        hardness_val = self._find_param_value(params, '总硬度')
        ca_val = self._find_param_value(params, '钙')
        mg_val = self._find_param_value(params, '镁')

        if hardness_val is None or ca_val is None or mg_val is None:
            return results

        h_num, h_lim = parse_numeric(str(hardness_val))
        ca_num, ca_lim = parse_numeric(str(ca_val))
        mg_num, mg_lim = parse_numeric(str(mg_val))

        if h_num is None or ca_num is None or mg_num is None:
            return results
        if h_lim or ca_lim or mg_lim:
            return results  # 含检出限不做计算

        calc = ca_num * 2.497 + mg_num * 4.118
        if h_num > 0:
            deviation = abs(calc - h_num) / h_num * 100
            if deviation > 15:
                results.append({
                    'level': 'warning',
                    'category': '关联一致性',
                    'sample': sid,
                    'indicator': '总硬度',
                    'message': (f'总硬度 {h_num} 与钙镁计算值 {calc:.1f} '
                                f'(Ca={ca_num}×2.497 + Mg={mg_num}×4.118) '
                                f'偏差 {deviation:.1f}%，超过15%'),
                })
            elif deviation > 8:
                results.append({
                    'level': 'notice',
                    'category': '关联一致性',
                    'sample': sid,
                    'indicator': '总硬度',
                    'message': (f'总硬度 {h_num} 与钙镁计算值 {calc:.1f} '
                                f'偏差 {deviation:.1f}%'),
                })

        return results

    def _check_thm_consistency(self, sid, params):
        """三卤甲烷(总量) = 各组分实测值/各自限值 之和"""
        results = []

        thm_total_val = self._find_param_value(params, '三卤甲烷')
        if thm_total_val is None:
            return results

        thm_num, thm_lim = parse_numeric(str(thm_total_val))
        if thm_num is None or thm_lim:
            return results

        # 各组分及其限值 (mg/L)
        components = {
            '三氯甲烷': 0.06,
            '四氯化碳': 0.002,
            '二氯一溴甲烷': 0.06,
            '一氯二溴甲烷': 0.1,
            '三溴甲烷': 0.1,
        }

        calc_sum = 0
        found_any = False
        for comp_name, comp_limit in components.items():
            comp_val = self._find_param_value(params, comp_name)
            if comp_val is None:
                continue
            comp_num, comp_is_lim = parse_numeric(str(comp_val))
            if comp_num is None:
                continue
            found_any = True
            calc_sum += comp_num / comp_limit

        if not found_any:
            return results

        if abs(calc_sum - thm_num) > 0.05 and thm_num > 0:
            deviation = abs(calc_sum - thm_num) / thm_num * 100
            if deviation > 20:
                results.append({
                    'level': 'warning',
                    'category': '关联一致性',
                    'sample': sid,
                    'indicator': '三卤甲烷',
                    'message': (f'三卤甲烷 {thm_num} 与各组分比值之和 '
                                f'{calc_sum:.4f} 偏差 {deviation:.1f}%'),
                })

        return results

    def _check_plant_consistency(self, samples, data):
        """同一水厂的出厂水与管网水关键指标不应有巨大差异"""
        results = []

        # 按水厂分组
        plant_groups = {}
        for s in samples:
            plant = s.get('被检水厂', '')
            stype = s.get('样品类型', '')
            if plant and stype in ('出厂水', '管网水'):
                plant_groups.setdefault(plant, []).append(s)

        # 需要对比的关键指标
        compare_params = ['pH', '浑浊度', '高锰酸盐指数', '电导率']

        for plant, group in plant_groups.items():
            if len(group) < 2:
                continue
            factory_samples = [s for s in group if s['样品类型'] == '出厂水']
            network_samples = [s for s in group if s['样品类型'] == '管网水']
            if not factory_samples or not network_samples:
                continue

            for param_key in compare_params:
                for fs in factory_samples:
                    fv_raw = self._find_param_value(data.get(fs['样品编号'], {}), param_key)
                    if fv_raw is None:
                        continue
                    fv, fl = parse_numeric(str(fv_raw))
                    if fv is None or fl:
                        continue

                    for ns in network_samples:
                        nv_raw = self._find_param_value(data.get(ns['样品编号'], {}), param_key)
                        if nv_raw is None:
                            continue
                        nv, nl = parse_numeric(str(nv_raw))
                        if nv is None or nl:
                            continue

                        if fv > 0:
                            diff_pct = abs(nv - fv) / fv * 100
                            if diff_pct > 50:
                                results.append({
                                    'level': 'warning',
                                    'category': '关联一致性',
                                    'sample': ns['样品编号'],
                                    'indicator': param_key,
                                    'message': (f'{plant}管网水({ns["样品编号"]}) '
                                                f'与出厂水({fs["样品编号"]}) 的 {param_key} '
                                                f'偏差 {diff_pct:.0f}% '
                                                f'(出厂={fv}, 管网={nv})'),
                                })

        return results

    def _find_param_value(self, params, keyword):
        """在参数字典中模糊查找指标值"""
        # 精确匹配
        if keyword in params:
            return params[keyword]
        # 前缀匹配（如 "总硬度" 匹配 "总硬度(以CaCO3计)(mg/L)"）
        for k, v in params.items():
            if k.startswith(keyword):
                return v
        # 包含匹配
        for k, v in params.items():
            if keyword in k:
                return v
        return None

    # ── 4. 元信息校核 ─────────────────────────────────────────────────

    def _check_metadata(self, samples, detection_date=None):
        results = []
        known_companies = self._get_known_companies()
        known_plants = self._get_known_plants()

        for s in samples:
            sid = s['样品编号']

            # 被检单位校验
            company = s.get('被检单位', '').strip()
            if company and known_companies and company not in known_companies:
                results.append({
                    'level': 'notice',
                    'category': '元信息',
                    'sample': sid,
                    'indicator': '',
                    'message': f'被检单位 "{company}" 不在系统已有单位中，请确认',
                })

            # 被检水厂校验
            plant = s.get('被检水厂', '').strip()
            if plant and known_plants and plant not in known_plants:
                results.append({
                    'level': 'notice',
                    'category': '元信息',
                    'sample': sid,
                    'indicator': '',
                    'message': f'被检水厂 "{plant}" 不在系统已有水厂中，请确认',
                })

            # 采样日期校验
            sampling_date_str = s.get('采样日期', '').strip()
            sampling_date = None
            if sampling_date_str:
                try:
                    sampling_date = datetime.strptime(sampling_date_str, '%Y-%m-%d').date()
                except ValueError:
                    results.append({
                        'level': 'error',
                        'category': '元信息',
                        'sample': sid,
                        'indicator': '',
                        'message': f'采样日期 "{sampling_date_str}" 格式不正确，应为 YYYY-MM-DD',
                    })

                if sampling_date:
                    today = date.today()
                    if sampling_date > today:
                        results.append({
                            'level': 'warning',
                            'category': '元信息',
                            'sample': sid,
                            'indicator': '',
                            'message': f'采样日期 {sampling_date_str} 晚于今天',
                        })
            else:
                results.append({
                    'level': 'warning',
                    'category': '元信息',
                    'sample': sid,
                    'indicator': '',
                    'message': '采样日期为空',
                })

            # 检测日期不能早于采样日期
            if detection_date and sampling_date:
                try:
                    det_date = datetime.strptime(detection_date, '%Y-%m-%d').date()
                    if det_date < sampling_date:
                        results.append({
                            'level': 'error',
                            'category': '元信息',
                            'sample': sid,
                            'indicator': '',
                            'message': (f'检测日期 {detection_date} 早于'
                                        f'采样日期 {sampling_date_str}'),
                        })
                except ValueError:
                    pass

            # 样品类型校验
            stype = s.get('样品类型', '').strip()
            if not stype:
                results.append({
                    'level': 'notice',
                    'category': '元信息',
                    'sample': sid,
                    'indicator': '',
                    'message': '样品类型为空，请确认',
                })

        return results

    # ── 5. 精度与格式校核 ─────────────────────────────────────────────

    def _check_precision(self, samples, data):
        results = []

        # 收集同一指标在不同样品中的检出限和小数位数
        indicator_stats = {}  # {param: {'limits': set, 'decimals': set, 'samples': list}}

        for s in samples:
            sid = s['样品编号']
            params = data.get(sid, {})
            for param, val in params.items():
                if val is None or is_text_indicator(param) or is_noise_indicator(param):
                    continue
                val_str = str(val).strip()
                if not val_str:
                    continue

                if param not in indicator_stats:
                    indicator_stats[param] = {
                        'limits': {},
                        'decimals': {},
                    }
                stats = indicator_stats[param]

                m = DETECTION_LIMIT_RE.match(val_str)
                if m:
                    limit_val = m.group(1)
                    stats['limits'].setdefault(limit_val, []).append(sid)
                    # 检出限的小数位数
                    if '.' in limit_val:
                        dec = len(limit_val.split('.')[1])
                        stats['decimals'].setdefault(dec, []).append(sid)
                elif NUMERIC_RE.match(val_str):
                    if '.' in val_str:
                        dec = len(val_str.rstrip('0').split('.')[1]) if '.' in val_str.rstrip('0') else 0
                        stats['decimals'].setdefault(dec, []).append(sid)
                else:
                    # 格式不规范的检出限（如 "< 0.010" 有多余空格，或使用全角符号）
                    if val_str.startswith('＜'):
                        results.append({
                            'level': 'notice',
                            'category': '精度与格式',
                            'sample': sid,
                            'indicator': param,
                            'message': f'检出限使用了全角符号 "＜"，建议统一为半角 "<"',
                        })
                    elif re.match(r'^<\s+\d', val_str):
                        results.append({
                            'level': 'notice',
                            'category': '精度与格式',
                            'sample': sid,
                            'indicator': param,
                            'message': f'检出限 "{val_str}" 中 "<" 后有多余空格',
                        })

        # 检查同一指标不同样品的检出限是否一致
        for param, stats in indicator_stats.items():
            if len(stats['limits']) > 1:
                limit_detail = ', '.join(
                    f'<{lv}({len(sids)}个样品)' for lv, sids in stats['limits'].items()
                )
                results.append({
                    'level': 'warning',
                    'category': '精度与格式',
                    'sample': '全部样品',
                    'indicator': param,
                    'message': f'同一指标存在不同检出限: {limit_detail}',
                })

        return results


# ── 便捷函数 ─────────────────────────────────────────────────────────────

def validate_samples(samples, data, detection_date=None, db_path=None):
    """便捷函数：对样品数据执行校核"""
    validator = RawDataValidator(db_path)
    return validator.validate(samples, data, detection_date)


def validate_from_database(sample_numbers, detection_date=None, db_path=None):
    """便捷函数：从数据库加载数据并校核"""
    validator = RawDataValidator(db_path)
    return validator.validate_from_db(sample_numbers, detection_date)


# ── CLI 测试入口 ─────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys
    import json
    from raw_data_converter import convert_raw_excel

    if len(sys.argv) < 2:
        print("用法: python raw_data_validator.py <input.xlsx> [检测日期]")
        sys.exit(1)

    src = sys.argv[1]
    det_date = sys.argv[2] if len(sys.argv) > 2 else None

    result = convert_raw_excel(src)
    if not result['success']:
        print(f"转换失败: {result['message']}")
        sys.exit(1)

    checks = validate_samples(result['samples'], result['data'], det_date)

    # 统计
    counts = {'error': 0, 'warning': 0, 'notice': 0}
    for c in checks:
        counts[c['level']] += 1

    print(f"\n校核结果: {len(checks)} 项 "
          f"(错误 {counts['error']}, 警告 {counts['warning']}, 提示 {counts['notice']})\n")

    for c in checks:
        icon = {'error': '✗', 'warning': '⚠', 'notice': '○'}[c['level']]
        indicator = f" [{c['indicator']}]" if c.get('indicator') else ''
        print(f"  {icon} [{c['category']}] {c['sample']}{indicator}: {c['message']}")
