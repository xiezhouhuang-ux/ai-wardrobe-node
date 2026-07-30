// 极简 JSON 文件存储，避免引入原生数据库依赖（MVP 足够）
import fs from 'node:fs';
import path from 'node:path';
import { CONFIG } from './config.js';

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function readDB() {
  ensureDir(CONFIG.PATHS.DATA);
  if (!fs.existsSync(CONFIG.PATHS.WARDROBE_DB)) {
    return { photos: [], items: [] };
  }
  try {
    return JSON.parse(fs.readFileSync(CONFIG.PATHS.WARDROBE_DB, 'utf8'));
  } catch {
    return { photos: [], items: [] };
  }
}

function writeDB(db) {
  ensureDir(CONFIG.PATHS.DATA);
  fs.writeFileSync(CONFIG.PATHS.WARDROBE_DB, JSON.stringify(db, null, 2), 'utf8');
}

export const store = {
  all() {
    return readDB();
  },

  addPhoto(photo) {
    const db = readDB();
    db.photos.push(photo);
    writeDB(db);
    return photo;
  },

  getPhoto(id) {
    return readDB().photos.find((p) => p.id === id) || null;
  },

  addItems(items) {
    const db = readDB();
    db.items.push(...items);
    writeDB(db);
    return items;
  },

  listItems() {
    return readDB().items;
  },

  getItem(id) {
    return readDB().items.find((i) => i.id === id) || null;
  },

  deleteItem(id) {
    const db = readDB();
    const item = db.items.find((i) => i.id === id);
    if (!item) return null;
    db.items = db.items.filter((i) => i.id !== id);
    writeDB(db);
    // 删除对应的单品图片
    if (item.imagePath && fs.existsSync(item.imagePath)) {
      try {
        fs.unlinkSync(item.imagePath);
      } catch {
        /* ignore */
      }
    }
    return item;
  },

  stats() {
    const db = readDB();
    const byCategory = {};
    const byColor = {};
    for (const it of db.items) {
      byCategory[it.category] = (byCategory[it.category] || 0) + 1;
      byColor[it.color] = (byColor[it.color] || 0) + 1;
    }
    return {
      totalItems: db.items.length,
      totalPhotos: db.photos.length,
      byCategory,
      byColor,
    };
  },
};

export function newId(prefix = 'id') {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export { path };
