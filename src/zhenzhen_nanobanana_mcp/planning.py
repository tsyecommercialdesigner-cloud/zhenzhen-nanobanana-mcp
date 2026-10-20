"""Deterministic, free ecommerce prompts; never invent product claims."""

from .models import AspectRatio, ImagePlan, ImageSpec, Resolution, Scene

COMPOSITIONS = {
    "main": [
        "单品主视觉，干净背景，商品主体完整清晰，突出真实材质",
        "商品组合与收纳关系，清晰呈现实际套装内容，不增加未提供配件",
    ],
    "detail": [
        "详情页开篇：商品全貌与主要使用价值",
        "详情页卖点：仅根据已提供的卖点展示功能细节",
        "详情页材质：微距呈现真实表面纹理和工艺",
        "详情页场景：在家居生活环境中呈现实际用途",
        "详情页尺寸：仅标注已提供的尺寸，未提供则不标尺寸",
        "详情页使用：仅展示已提供的操作方法，不编造安全效果",
    ],
    "scene": ["自然家居使用场景，光线柔和，背景与商品用途一致"],
    "poster": ["电商营销海报，商品醒目，文案排版清晰，保留适度留白"],
}


def build_plan(
    product_name: str,
    selling_points: list[str],
    scene: Scene,
    count: int,
    aspect_ratio: AspectRatio,
    reference_images: list[str],
    requirements: str,
    copy_text: str,
    resolution: Resolution | None = None,
) -> ImagePlan:
    items = []
    for index in range(count):
        composition = COMPOSITIONS[scene][index % len(COMPOSITIONS[scene])]
        prompt = (
            f"为家居日用百货商品制作电商图片。商品：{product_name}。\n"
            f"本张构图：{composition}。这是第 {index + 1} 张，请区分构图与视角。\n"
            f"已提供的商品事实与卖点：{'；'.join(selling_points) or '未提供'}。\n"
            f"用户要求：{requirements or '无额外要求'}。\n"
            f"图片中的指定文案：{copy_text or '不添加文字'}。\n"
            "保留参考图商品的外形、比例、颜色、材质、品牌与包装细节。"
            "只使用已提供的商品事实，不捏造尺寸、认证、功效、销量或促销价格。"
            "不要增加未提供的配件，商品展示与真实用途一致。"
        )
        items.append(
            ImageSpec(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                reference_images=reference_images,
                resolution=resolution,
            )
        )
    return ImagePlan(
        product_name=product_name,
        scene=scene,
        items=items,
        notes=[
            "此计划不调用绘图 API。请先核对商品事实、文案与具体平台要求。",
            "参考图非空时执行编辑；模型保持商品一致性的效果需人工检查。",
            "每个 item 为一次独立绘图请求，收费与平台审核结果由上游/平台决定。",
        ],
    )
