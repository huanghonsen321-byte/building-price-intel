SCAFFOLD_EXTRACT_SYSTEM_PROMPT = """你是建筑工程招投标公告结构化抽取助手。只输出 JSON，不输出解释。"""

SCAFFOLD_EXTRACT_USER_PROMPT = """请从以下公告正文中抽取脚手架/周转材料相关字段。
字段必须包括：is_scaffold_related, announcement_type, project_name, province, city, district, buyer, agency, winner, bid_amount, publish_date, scaffold_type, procurement_type, service_scope, duration_text, quantity_text, area_m2, tonnage, rental_days, pricing_method, unit_price_candidates, ai_summary, missing_fields, confidence。
无法确定的字段填 null 或空数组。

公告正文：
{text}
"""
