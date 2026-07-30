// ============================================================
//  AI Wardrobe · 服务管理脚本（零依赖，跨平台 Node 脚本）
//  用法：
//    node service.js start     启动（后台守护）
//    node service.js stop      停止
//    node service.js restart   重启
//    node service.js status    查看运行状态
//    node service.js logs      打印日志文件路径
//  说明：
//    - 通过 PID 文件管理进程，不依赖 shell 的 rm/kill 限制。
//    - server.js 内部会自行加载 .env，无需在此重复设置。
// ============================================================
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import './lib/env.js'; // 加载 .env，使 PORT 等配置在 status 输出时正确

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = __dirname;
const PID_FILE = path.join(ROOT, '.ai-wardrobe.pid');
const LOG_DIR = path.join(ROOT, 'logs');
const LOG_FILE = path.join(LOG_DIR, 'ai-wardrobe.out.log');

function port() {
  return process.env.PORT || 3000;
}

function readPid() {
  try {
    return parseInt(fs.readFileSync(PID_FILE, 'utf8').trim(), 10);
  } catch {
    return null;
  }
}

function isAlive(pid) {
  if (!pid) return false;
  try {
    process.kill(pid, 0); // 信号 0：仅检测存在性，不真正发送
    return true;
  } catch {
    return false;
  }
}

function writePid(pid) {
  fs.writeFileSync(PID_FILE, String(pid));
}

function removePid() {
  try {
    fs.unlinkSync(PID_FILE);
  } catch {
    /* 忽略：文件可能不存在 */
  }
}

async function start() {
  const pid = readPid();
  if (isAlive(pid)) {
    console.log(`已在运行 (PID ${pid})。访问 http://localhost:${port()}`);
    return;
  }
  if (!fs.existsSync(LOG_DIR)) fs.mkdirSync(LOG_DIR, { recursive: true });

  const logFd = fs.openSync(LOG_FILE, 'a');
  const child = spawn(process.execPath, ['server.js'], {
    cwd: ROOT,
    detached: true, // 脱离父进程，成为独立后台守护
    env: process.env,
    stdio: ['ignore', logFd, logFd],
  });
  child.unref();

  writePid(child.pid);
  console.log(
    `已启动 (PID ${child.pid})\n  访问: http://localhost:${port()}\n  日志: ${LOG_FILE}`
  );
}

async function stop() {
  const pid = readPid();
  if (!pid || !isAlive(pid)) {
    console.log('未运行。');
    removePid();
    return;
  }
  try {
    process.kill(pid, 'SIGTERM');
  } catch {
    /* 忽略 */
  }
  // 等待最多 4 秒优雅退出
  for (let i = 0; i < 20; i++) {
    if (!isAlive(pid)) break;
    await new Promise((r) => setTimeout(r, 200));
  }
  if (isAlive(pid)) {
    try {
      process.kill(pid, 'SIGKILL'); // 强制结束
    } catch {
      /* 忽略 */
    }
  }
  removePid();
  console.log('已停止。');
}

async function status() {
  const pid = readPid();
  if (isAlive(pid)) {
    console.log(`运行中 (PID ${pid})，访问 http://localhost:${port()}`);
  } else {
    console.log('未运行。');
    removePid();
  }
}

const cmd = process.argv[2];
switch (cmd) {
  case 'start':
    await start();
    break;
  case 'stop':
    await stop();
    break;
  case 'restart':
    await stop();
    await start();
    break;
  case 'status':
    await status();
    break;
  case 'logs':
    console.log(LOG_FILE);
    break;
  default:
    console.log('用法: node service.js {start|stop|restart|status|logs}');
    process.exit(1);
}
