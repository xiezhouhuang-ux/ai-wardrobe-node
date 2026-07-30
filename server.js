import express from 'express';
import multer from 'multer';
import fs from 'node:fs';
import path from 'node:path';
import { CONFIG } from './lib/config.js';
import { store, newId } from './lib/store.js';
import { detectClothing } from './lib/qwen.js';
import { extractItem } from './lib/segment.js';

const app = express();
app.use(express.json());

// 静态资源
app.use('/uploads', express.static(CONFIG.PATHS.UPLOADS));
app.use('/items', express.static(CONFIG.PATHS.ITEMS));
app.use(express.static(path.join(CONFIG.PATHS.ROOT, 'public')));

// 上传配置：保存到 uploads/
const upload = multer({
  storage: multer.diskStorage({
    destination: (req, file, cb) => cb(null, CONFIG.PATHS.UPLOADS),
    filename: (req, file, cb) => {
      const id = newId('ph');
      const ext = (path.extname(file.originalname) || '.jpg').toLowerCase();
      cb(null, `${id}${ext}`);
    },
  }),
  limits: { fileSize: 20 * 1024 * 1024, files: 20 },
  fileFilter: (req, file, cb) => {
    if (/image\/(jpeg|png|webp)/.test(file.mimetype)) cb(null, true);
    else cb(new Error('仅支持 JPG/PNG/WEBP 图片'));
  },
});

// 前端获取运行模式（demo / 真实 Qwen）
app.get('/api/config', (req, res) => {
  res.json({
    demoMode: CONFIG.DEMO_MODE,
    visionModel: CONFIG.QWEN_MODEL, // 模型 A：标签/检测
    imageModel: CONFIG.IMAGE_MODEL, // 模型 B：服饰分割
    cutoutEnabled: CONFIG.ENABLE_CUTOUT,
  });
});

// 核心接口：上传照片 -> AI 检测 -> 抠图 -> 入库
app.post('/api/process', upload.array('photos', 20), async (req, res) => {
  try {
    const files = req.files || [];
    if (files.length === 0) return res.status(400).json({ error: '未收到图片' });

    const result = [];
    for (const file of files) {
      const photoId = path.basename(file.filename, path.extname(file.filename));
      const photoRel = `/uploads/${file.filename}`;
      store.addPhoto({
        id: photoId,
        filename: file.filename,
        url: photoRel,
        createdAt: new Date().toISOString(),
      });

      const detections = await detectClothing(file.path);
      const items = [];
      for (const d of detections) {
        const itemId = newId('it');
        const outFile = `${itemId}.png`;
        const outPath = path.join(CONFIG.PATHS.ITEMS, outFile);
        // 模型 A（qwen-vl）给出类别与定位 box；模型 B（qwen-image）直接对原图分割对应单品
        const { transparent, segmentMethod } = await extractItem(file.path, d, outPath);
        const item = {
          id: itemId,
          category: d.category,
          color: d.color,
          season: d.season,
          material: d.material,
          style: d.style,
          fit: d.fit,
          pattern: d.pattern,
          brand: d.brand,
          hasLogo: d.hasLogo,
          imageUrl: `/items/${outFile}`,
          transparent,
          segmentMethod,
          sourcePhoto: photoRel,
          createdAt: new Date().toISOString(),
        };
        items.push(item);
      }
      store.addItems(items);
      result.push({ photoId, photoUrl: photoRel, items });
    }
    res.json({ ok: true, demoMode: CONFIG.DEMO_MODE, result });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: e.message || '处理失败' });
  }
});

app.get('/api/items', (req, res) => {
  res.json(store.listItems());
});

app.get('/api/items/:id', (req, res) => {
  const item = store.getItem(req.params.id);
  if (!item) return res.status(404).json({ error: 'not found' });
  res.json(item);
});

app.delete('/api/items/:id', (req, res) => {
  const item = store.deleteItem(req.params.id);
  if (!item) return res.status(404).json({ error: 'not found' });
  res.json({ ok: true });
});

app.get('/api/stats', (req, res) => {
  res.json(store.stats());
});

app.listen(CONFIG.PORT, () => {
  console.log(`\n  AI Wardrobe (Phase 1 MVP) 已启动`);
  console.log(`  ➜  http://localhost:${CONFIG.PORT}`);
  console.log(
    CONFIG.DEMO_MODE
      ? `  ⚠️  未检测到 QWEN_API_KEY，当前为 DEMO 模式（mock 结果）。\n      设置环境变量 QWEN_API_KEY 后重启即可使用真实 Qwen 分析。\n`
      : `  ✅ 已接入 Qwen 模型: ${CONFIG.QWEN_MODEL}\n`
  );
});
