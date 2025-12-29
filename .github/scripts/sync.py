import os
import subprocess
import hashlib

# --- 路径配置 ---
# 在 GitHub Actions 中，目录结构通常为：
# /home/runner/work/repo-name/repo-name/ (当前工作目录)
# ├── homebrew-core/
# └── homebrew-sdkman/
BASE_DIR = os.getcwd()
CORE_DIR = os.path.join(BASE_DIR, "homebrew-core")
SDK_DIR = os.path.join(BASE_DIR, "homebrew-sdkman")

TARGET_DEP = 'depends_on "openjdk"'
COMMENTED_DEP = '# depends_on "openjdk"'

def get_logic_hash(content):
    """计算逻辑哈希：排除掉注释差异，只对比代码本体"""
    normalized = content.replace(COMMENTED_DEP, TARGET_DEP)
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()

def run_command(command, cwd):
    """执行命令并返回输出，不因非零返回码崩溃"""
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        print(f"执行命令出错: {e}")
        return None

def sync_formulae():
    # 定位 Core 中的 Formula 目录
    # 适配不同版本的 Homebrew 目录结构
    search_base = os.path.join(CORE_DIR, "Formula")
    if not os.path.exists(search_base):
        search_base = CORE_DIR

    print(f"🔍 正在递归扫描 Core 仓库: {search_base}")

    sync_count = 0

    for root, dirs, files in os.walk(search_base):
        for file_name in files:
            if not file_name.endswith(".rb"):
                continue

            # 源文件完整路径
            src_file_path = os.path.join(root, file_name)
            
            # 计算相对于 Core 根目录的路径，用于在 SDK 中保持一致
            rel_path = os.path.relpath(src_file_path, CORE_DIR)
            dst_file_path = os.path.join(SDK_DIR, rel_path)

            try:
                with open(src_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                print(f"⚠️ 读取失败 {file_name}: {e}")
                continue

            # 只处理包含 openjdk 依赖的文件
            if TARGET_DEP in content:
                # 如果目标文件已存在，对比逻辑哈希
                if os.path.exists(dst_file_path):
                    with open(dst_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        dst_content = f.read()
                    if get_logic_hash(content) == get_logic_hash(dst_content):
                        continue

                # 确保目标目录存在
                os.makedirs(os.path.dirname(dst_file_path), exist_ok=True)

                # 转换内容
                new_content = content.replace(TARGET_DEP, COMMENTED_DEP)
                with open(dst_file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                # 提取 Git 提交信息用于备注
                # 注意：rel_path 必须是相对于 core 根目录的路径
                commit_sha = run_command(['git', 'log', '-1', '--format=%h', '--', rel_path], CORE_DIR)
                commit_msg = run_command(['git', 'log', '-1', '--format=%s', '--', rel_path], CORE_DIR)

                # 添加到 SDK 暂存区
                run_command(['git', 'add', rel_path], SDK_DIR)
                
                # 检查是否有实际变动（防止空提交）
                status = run_command(['git', 'status', '--porcelain', rel_path], SDK_DIR)
                if status:
                    full_msg = (
                        f"Sync {file_name} from core@{commit_sha or 'unknown'}\n\n"
                        f"Original: {commit_msg or 'No message'}\n"
                        f"Action: Auto-commented openjdk dependency."
                    )
                    run_command(['git', 'commit', '-m', full_msg], SDK_DIR)
                    print(f"✅ 已同步并提交: {rel_path}")
                    sync_count += 1

    print(f"\n✨ 同步任务结束。共更新了 {sync_count} 个组件。")

if __name__ == "__main__":
    # 验证环境
    if not os.path.exists(SDK_DIR):
        print(f"❌ 找不到 SDK 目录: {SDK_DIR}")
    elif not os.path.exists(CORE_DIR):
        print(f"❌ 找不到 Core 目录: {CORE_DIR}")
    else:
        sync_formulae()