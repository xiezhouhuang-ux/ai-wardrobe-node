// 配置中心：所有可调参数集中在此
import './env.js'; // 必须在读取 process.env 前加载 .env
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');

// API Key 仅来自 .env / 环境变量；未设置则进入 DEMO 模式（不内置任何密钥，避免意外计费/泄露）
const API_KEY = (process.env.QWEN_API_KEY || '').trim();

// 视觉理解（标签/检测）模型走 OpenAI 兼容接口（默认百炼公网地址；MaaS 用户用 QWEN_BASE_URL 覆盖）
const VISION_BASE_URL =
  process.env.QWEN_BASE_URL || 'https://dashscope.aliyuncs.com/compatible-mode/v1';

// 图像生成/编辑（服饰分割）模型走 DashScope 多模态生成接口（默认百炼公网地址；MaaS 用户用 QWEN_IMAGE_ENDPOINT 覆盖）
const IMAGE_ENDPOINT =
  process.env.QWEN_IMAGE_ENDPOINT ||
  'https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation';

export const CONFIG = {
  // 模型 A：视觉理解（属性标签 + 单品定位），OpenAI 兼容接口
  QWEN_API_KEY: API_KEY,
  QWEN_MODEL: process.env.QWEN_MODEL || 'qwen2.5-vl-72b-instruct',
  QWEN_BASE_URL: VISION_BASE_URL,

  // 模型 B：图像生成/编辑（服饰分割 / 去背景 / 补全），多模态生成接口
  IMAGE_MODEL: process.env.QWEN_IMAGE_MODEL || 'qwen-image-2.0-pro',
  IMAGE_ENDPOINT,

  // 无 API Key 进入 demo 模式（mock 结果，仅演示流程）
  get DEMO_MODE() {
    return !API_KEY;
  },

  // 是否启用本地透明背景抠图（依赖 @imgly/background-removal-node）作为离线兜底
  ENABLE_CUTOUT: process.env.ENABLE_CUTOUT !== '0',

  PORT: Number(process.env.PORT || 3000),

  PATHS: {
    ROOT,
    UPLOADS: path.join(ROOT, 'uploads'),
    ITEMS: path.join(ROOT, 'items'),
    DATA: path.join(ROOT, 'data'),
    WARDROBE_DB: path.join(ROOT, 'data', 'wardrobe.json'),
  },
};
