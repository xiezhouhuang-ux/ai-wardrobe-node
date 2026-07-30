// Qwen 视觉分析：调用阿里云百炼 qwen-vl，输出服装检测 + 标签（无 box）
// 无 API Key 时进入 demo 模式，返回合理 mock 结果（仅用于演示完整流程）
// 说明：本方案不要求模型输出包围盒；服饰分割交由 qwen-image 在原图上完成。
import fs from 'node:fs';
import { CONFIG } from './config.js';
import { SYSTEM_PROMPT, buildUserMessage } from './prompt.js';

// 从模型可能夹带的文本中提取 JSON 数组
function extractJSON(text) {
  if (!text) return [];
  let t = text.trim();
  // 去掉 ```json ... ``` 包裹
  const fence = t.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fence) t = fence[1].trim();
  // 截取第一个 [ 到最后一个 ]
  const s = t.indexOf('[');
  const e = t.lastIndexOf(']');
  if (s === -1 || e === -1 || e < s) return [];
  try {
    return JSON.parse(t.slice(s, e + 1));
  } catch {
    return [];
  }
}

// 四大类（唯一合法类别，内部用英文做校验）
const VALID_CATEGORIES = ['Top', 'Bottom', 'Shoes', 'Bag'];

// ---------- 中文字典：把模型返回的英文受控词统一转换为中文存储 ----------
const CATEGORY_CN = { Top: '上装', Bottom: '下装', Shoes: '鞋', Bag: '包' };
const COLOR_CN = {
  White: '白色', Black: '黑色', Blue: '蓝色', Beige: '米色', Red: '红色',
  Green: '绿色', Gray: '灰色', Grey: '灰色', Pink: '粉色', Brown: '棕色',
  Yellow: '黄色', Purple: '紫色', Multicolor: '多色', Unknown: '未知',
};
const SEASON_CN = {
  Spring: '春季', Summer: '夏季', Autumn: '秋季', Fall: '秋季',
  Winter: '冬季', All: '四季', Unknown: '四季',
};
const MATERIAL_CN = {
  Cotton: '棉', Denim: '牛仔布', Leather: '皮革', Knit: '针织',
  Polyester: '聚酯纤维', Silk: '丝绸', Linen: '亚麻', Wool: '羊毛', Unknown: '未知',
};
const STYLE_CN = {
  Minimal: '极简', Casual: '休闲', Sporty: '运动', Formal: '正装', Vintage: '复古',
  Y2K: 'Y2K', Streetwear: '街头', French: '法式', OldMoney: '老钱风',
  Preppy: '学院风', Athleisure: '运动休闲', Unknown: '未知',
};
const FIT_CN = { Slim: '修身', Regular: '常规', Loose: '宽松', Oversized: '超大', Unknown: '未知' };
const PATTERN_CN = {
  Solid: '纯色', Striped: '条纹', Floral: '碎花', Plaid: '格纹',
  Dotted: '波点', Graphic: '图案', Other: '其它', Unknown: '其它',
};

// 英文名 → 中文；未知/异常时回退
function toCn(map, v, fallback = '未知') {
  const key = String(v || '').trim();
  return map[key] || (key ? key : fallback);
}

// 类别别名 → 规范类别。
// 连衣裙/外套/大衣/西装/夹克 统一归入上装(Top)；其余（含配饰）一律丢弃。
const CATEGORY_ALIASES = {
  top: 'Top', '上装': 'Top', '上衣': 'Top', '上裝': 'Top',
  bottom: 'Bottom', '下装': 'Bottom', '裤子': 'Bottom', '裤': 'Bottom', '下裝': 'Bottom',
  shoes: 'Shoes', '鞋': 'Shoes', '鞋子': 'Shoes', '鞋类': 'Shoes',
  bag: 'Bag', '包': 'Bag', '包包': 'Bag', '包类': 'Bag',
  // 归入上装
  dress: 'Top', '连衣裙': 'Top', '连身裙': 'Top',
  outerwear: 'Top', '外套': 'Top', '大衣': 'Top', 'coat': 'Top', 'jacket': 'Top', '夹克': 'Top',
  suit: 'Top', '西装': 'Top', '西裝': 'Top',
};

// 将模型给出的类别归一为规范类别；无法识别（如配饰）返回 null（将被丢弃）
function canonicalCategory(raw) {
  const c = String(raw || '').trim();
  if (!c) return null;
  const lower = c.toLowerCase();
  if (CATEGORY_ALIASES[lower]) return CATEGORY_ALIASES[lower];
  if (VALID_CATEGORIES.includes(c)) return c;
  return null;
}

function normalizeItem(raw) {
  const catEn = canonicalCategory(raw.category);
  if (!catEn) return null; // 过滤掉配饰等无关类别
  const seasonEn = ['Spring', 'Summer', 'Autumn', 'Winter', 'All'].includes(raw.season)
    ? raw.season
    : 'All';
  return {
    category: CATEGORY_CN[catEn] || catEn,
    color: toCn(COLOR_CN, raw.color, '未知'),
    season: SEASON_CN[seasonEn] || '四季',
    material: toCn(MATERIAL_CN, raw.material, '未知'),
    style: toCn(STYLE_CN, raw.style, '未知'),
    fit: toCn(FIT_CN, raw.fit, '未知'),
    pattern: toCn(PATTERN_CN, raw.pattern, '纯色'),
    brand: String(raw.brand || 'Unknown').trim() || 'Unknown',
    hasLogo: !!raw.hasLogo,
  };
}

// ---------- 去重：每个类别最多保留一件 ----------
// 无包围盒后无法用 IoU；改为按类别去重（保留最先出现的那件）。
function dedupItems(items) {
  const seen = new Set();
  const out = [];
  for (const item of items) {
    if (seen.has(item.category)) continue;
    seen.add(item.category);
    out.push(item);
  }
  return out;
}

async function callQwen(base64, mediaType) {
  const res = await fetch(`${CONFIG.QWEN_BASE_URL}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${CONFIG.QWEN_API_KEY}`,
    },
    body: JSON.stringify({
      model: CONFIG.QWEN_MODEL,
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: buildUserMessage(base64, mediaType) },
      ],
      temperature: 0.1,
      max_tokens: 2000,
    }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`${CONFIG.QWEN_MODEL} - Qwen API ${res.status}: ${err}`);
  }
  const data = await res.json();
  const content = data?.choices?.[0]?.message?.content || '';
  return extractJSON(content);
}

// demo 模式：返回四大类各一件（仅用于跑通流程，无需 box）
function demoDetect() {
  const mk = (cat, extra) => ({
    category: cat,
    color: extra.color,
    season: extra.season,
    material: extra.material,
    style: extra.style,
    fit: extra.fit,
    pattern: extra.pattern,
    brand: 'Unknown',
    hasLogo: false,
  });
  return [
    mk('Top', {
      color: 'White', season: 'Summer', material: 'Cotton', style: 'Minimal', fit: 'Loose', pattern: 'Solid',
    }),
    mk('Bottom', {
      color: 'Blue', season: 'All', material: 'Denim', style: 'Casual', fit: 'Regular', pattern: 'Solid',
    }),
    mk('Shoes', {
      color: 'White', season: 'All', material: 'Leather', style: 'Sporty', fit: 'Regular', pattern: 'Solid',
    }),
    mk('Bag', {
      color: 'Brown', season: 'All', material: 'Leather', style: 'Formal', fit: 'Regular', pattern: 'Solid',
    }),
  ];
}

export async function detectClothing(imagePath) {
  const buf = fs.readFileSync(imagePath);
  const base64 = buf.toString('base64');
  const ext = imagePath.split('.').pop().toLowerCase();
  const mediaType =
    ext === 'png' ? 'image/png' : ext === 'webp' ? 'image/webp' : 'image/jpeg';

  let raw;
  if (CONFIG.DEMO_MODE) {
    raw = demoDetect();
  } else {
    raw = await callQwen(base64, mediaType);
  }
  // 1) 规范化 + 过滤非法类别；2) 按类别去重
  const normalized = raw.map((r) => normalizeItem(r)).filter(Boolean);
  return dedupItems(normalized);
}

// 导出内部辅助函数，便于单元测试
export { canonicalCategory, dedupItems, normalizeItem };
