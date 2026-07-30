// 极简 dotenv：读取项目根目录 .env，注入 process.env（不覆盖已存在的变量）
// 零依赖，ESM。被 config.js 在读取环境变量前自动加载一次。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const ENV_PATH = path.join(ROOT, '.env');

export function loadEnv() {
  if (process.env.AI_WARDROBE_ENV_LOADED) return; // 幂等，避免重复加载
  process.env.AI_WARDROBE_ENV_LOADED = '1';

  if (!fs.existsSync(ENV_PATH)) return; // 无 .env 则用真实环境变量（如 DEMO 模式）

  const text = fs.readFileSync(ENV_PATH, 'utf8');
  for (const rawLine of text.split('\n')) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const eq = line.indexOf('=');
    if (eq === -1) continue;
    const key = line.slice(0, eq).trim();
    let val = line.slice(eq + 1).trim();
    // 去掉引号包裹
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    if (key && process.env[key] === undefined) {
      process.env[key] = val;
    }
  }
}

loadEnv();
