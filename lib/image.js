// 模型 B：调用 qwen-image 系列模型，直接基于【原图 + 类别提示词】识别并分割对应单品
// 不再依赖本地裁剪（sharp extract）——交由图像模型自行定位、分离、补全。
// 接口：DashScope 多模态生成 /api/v1/services/aigc/multimodal-generation/generation
import { CONFIG } from './config.js';

const TIMEOUT_MS = 120000;

// 中文类别描述，用于提示词让图像模型聚焦正确单品
const CATEGORY_CN = {
  Top:    { cn: '上装', desc: '如 T恤、衬衫、卫衣、毛衣、外套、西装、连衣裙等' },
  Bottom: { cn: '下装', desc: '如裤子、牛仔裤、半身裙、短裤等' },
  Shoes:  { cn: '鞋',   desc: '如运动鞋、皮鞋、靴子、凉鞋等' },
  Bag:    { cn: '包',   desc: '如手提包、双肩包、单肩包、腰包等' },
};

function toDataURI(buf, mime = 'image/png') {
  const b64 = buf.toString('base64');
  return `data:${mime};base64,${b64}`;
}

async function fetchToBuffer(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`下载分割结果失败 HTTP ${r.status}`);
  return Buffer.from(await r.arrayBuffer());
}

// 其它类别的排除清单：请求某一类时，严格排除清单中的类别，避免上装下装混在同一张输出
const EXCLUDE_OTHERS = {
  Top: '下装（裤子/裙）、鞋、包',
  Bottom: '上装、鞋、包',
  Shoes: '上装、下装、包',
  Bag: '上装、下装、鞋',
};

// 构造分割提示词：直接对【原图】识别并分离目标单品，不再依赖本地裁剪或包围盒
function buildSegmentPrompt(meta) {
  const cat = meta?.category || '服饰单品';
  const info = CATEGORY_CN[cat] || { cn: cat, desc: '' };
  const exclude = EXCLUDE_OTHERS[cat] || '其它衣物、人体、背景';
  const parts = [
    `你是一名专业的服装抠图与分割助手。请处理这张穿搭照片：`,
    `1) 在照片中【定位并仅提取】其中的「${info.cn}」（${info.desc}）。`,
    `2) 【严格排除】以下类别绝对不能出现在本图中：${exclude}。即使它们在原图中与目标单品相邻或重叠，也必须剔除，只保留目标单品本身。`,
    `3) 将该单品与人物、其它服饰、背景【完全分离】，输出透明背景的独立单品图（带 alpha 通道）。`,
    `4) 将该单品【正面居中】展示，严格保持原始颜色、版型、图案与材质，不得改变。`,
    `5) 合理推断并补全被遮挡、折叠或缺失的部分，使单品完整自然。`,
    `6) 不要生成模特、人体、姿势或任何场景；只输出该服装单品本身。`,
    `Isolate ONLY this ${info.cn} from the whole photo. Strictly exclude all other garments (${exclude}), the person, and the background. Transparent background, front view, centered, high quality product photo.`,
  ];
  return parts.join('');
}

/**
 * 调用 qwen-image 编辑接口，基于原图分割出目标单品。
 * @param {Buffer} imageBuffer 原图（未裁剪）
 * @param {object} meta 单品属性（category 等，用于构造提示词）
 * @returns {Buffer} 分割后的 PNG 二进制
 */
export async function segmentWithQwenImage(imageBuffer, meta) {
  const body = {
    model: CONFIG.IMAGE_MODEL,
    input: {
      messages: [
        {
          role: 'user',
          content: [
            { image: toDataURI(imageBuffer) },
            { text: buildSegmentPrompt(meta) },
          ],
        },
      ],
    },
    parameters: { n: 1, size: '1024*1024', watermark: false, prompt_extend: true },
  };

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(CONFIG.IMAGE_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${CONFIG.QWEN_API_KEY}`,
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`qwen-image HTTP ${res.status}: ${text.slice(0, 300)}`);
    }
    const data = await res.json();
    const content = data?.output?.choices?.[0]?.message?.content || [];
    const imageUrl = (Array.isArray(content) ? content : []).find((c) => c?.image)?.image;
    if (!imageUrl) {
      throw new Error('qwen-image 响应缺少 image: ' + JSON.stringify(data).slice(0, 300));
    }
    return await fetchToBuffer(imageUrl);
  } finally {
    clearTimeout(timer);
  }
}
