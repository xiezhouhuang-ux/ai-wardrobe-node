"""
提示词模块。复刻原 lib/prompt.js 的 SYSTEM_PROMPT 与用户消息构造逻辑。
"""

SYSTEM_PROMPT = """
你是一个专业的服装视觉识别助手。请仔细查看用户上传的穿搭照片，识别图中所有可识别的**独立单品**（一件上衣、一条裤子、一双鞋、一个包等各算一个单品）。

识别规则：
1. 只输出能被清晰辨认的单品；模糊、被遮挡超过一半、或无法确认类别的请忽略。
2. 对每一个单品，给出如下字段：
   - category：必须是以下之一：上衣（上衣，含T恤/衬衫/卫衣/毛衣/外套/大衣/西装/夹克/连身裙/连衣裙等）、下装（下装，含裤子/半身裙）、鞋（鞋，含运动鞋/靴子）、包（包，含背包/手提包）
   - color：中文颜色词 ，可以是多种
   - season：适用季节，取值之一：春 / 夏 / 秋 / 冬 / 四季
   - material：材质，如 棉 / 牛仔 / 针织 / 皮革 / 帆布 / 羽绒 / 涤纶 / 雪纺 等（不确定可写 未知）
   - style：风格，如 休闲 / 运动 / 通勤 / 极简 / 复古 / 学院 / 街头 / 温柔 等
   - fit：版型，如 宽松 / 修身 / 直筒 /  oversize / 常规 等（不确定可写 常规）
   - pattern：图案，如 纯色 / 条纹 / 格子 / 印花 / 拼色 / Logo 等（不确定可写 纯色）

输出要求：
- 必须以 JSON 数组返回，例如：[{"category":"上衣","color":"白","season":"夏","material":"棉","style":"休闲","fit":"宽松","pattern":"纯色"}]
- 不要输出任何解释文字、不要使用 markdown 代码块，只输出能被 JSON.parse 解析的纯 JSON。
- 如果没有识别到任何单品，返回空数组 []。
""".strip()


def build_user_message(media_type: str, base64_data: str) -> list:
    return [
        {
            "type": "text",
            "text": "请识别这张穿搭照片中的独立服装单品，并严格按照 system 指令以 JSON 数组返回。",
        },
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:{media_type};base64,{base64_data}",
            },
        },
    ]


def build_segment_prompt(meta: dict) -> str:
    """
    构造“把指定单品从原图抠出”的严格提示词。
    meta 来自 /api/analyze 返回的候选单品（已含中文归一化字段）。
    """
    category = meta.get("category", "")
    color = meta.get("color", "")
    material = meta.get("material", "")
    style = meta.get("style", "")
    pattern = meta.get("pattern", "")

    # 类别中文描述（analyze 已返回中文，这里做兜底映射）
    cat_zh = {
        "Top": "上衣", "Bottom": "下装", "Shoes": "鞋", "": "包",
    }.get(category, category)

    subject = f"这件{cat_zh}"
    traits = []
    if color:
        traits.append(color)
    if material and material not in ("未知",):
        traits.append(material)
    if style and style not in ("休闲",):
        traits.append(style)
    if pattern and pattern not in ("纯色",):
        traits.append(pattern)
    if traits:
        subject += "（" + "、".join(traits) + "）"

    prompt = (
        f"请对这张图片执行【单品抠图 / 主体分割】任务：\n"
        f"1. 只保留图片中的{subject}，将其完整、干净地提取出来。\n"
        f"2. 移除画面中所有其他人物、背景、其他服装与杂物，只保留目标单品本身。\n"
        f"3. 保持该单品的原始比例、轮廓与细节完整，不要拉伸、变形或补全缺失部分。\n"
        f"4. 最终输出为纯白色背景（#FFFFFF）的独立单品卡片，四周留有适当留白。\n"
        f"5. 这是服装单品分割，不要做任何风格转换、换色或重绘，仅做抠图。\n"
        f"请直接输出白底的单品图片。"
    )
    return prompt.strip()
