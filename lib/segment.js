// 单品提取编排（新方案，无裁剪）：
//   不再做本地裁剪（sharp extract）。直接把【原图】交给模型 B（qwen-image），
//   配合「类别 + 区域」提示词，由图像模型自行识别并分割出对应单品。
//   DEMO 模式 / 无 Key / 调用失败时，降级为原图本身（不做任何裁剪），保证流程不中断。
import sharp from 'sharp';
import fs from 'node:fs/promises';
import { CONFIG } from './config.js';
import { segmentWithQwenImage } from './image.js';

/**
 * 提取单品：原图 + qwen-image 提示词，直接分割出对应单品。
 * @param {string} imagePath 原图路径（全程不再裁剪）
 * @param {object} meta      单品属性（category / box 等，用于构造提示词）
 * @param {string} outPath   输出 PNG 路径
 * @returns {{ transparent: boolean, segmentMethod: 'qwen-image' | 'demo-original' }}
 */
export async function extractItem(imagePath, meta = {}, outPath) {
  const originalBuffer = await fs.readFile(imagePath);

  // DEMO 模式（未配置 Key）：无图像模型可用，直接落原图（不做任何裁剪）
  if (CONFIG.DEMO_MODE) {
    await normalizeToPng(originalBuffer, outPath);
    return { transparent: false, segmentMethod: 'demo-original' };
  }

  // LIVE 模式：模型 B（qwen-image）基于原图 + 类别提示词，识别并分割对应单品
  try {
    const seg = await segmentWithQwenImage(originalBuffer, meta);
    await normalizeToPng(seg, outPath);
    return { transparent: true, segmentMethod: 'qwen-image' };
  } catch (e) {
    console.warn('[segment] qwen-image 分割失败，降级为原图:', e.message);
    await normalizeToPng(originalBuffer, outPath);
    return { transparent: false, segmentMethod: 'demo-original' };
  }
}

// 统一转成 PNG 写出（保证前端按 .png 扩展名正确渲染）
async function normalizeToPng(buf, outPath) {
  try {
    await sharp(buf).png().toFile(outPath);
  } catch {
    // 极端兜底：无法解码时原样写出
    await fs.writeFile(outPath, buf);
  }
}
