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
    """执行命令并返回输出"""
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    except:
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
                commit_date = run_command(['git', 'log', '-1', '--format=%ai', '--', rel_path], CORE_DIR)

                # Git 暂存与提交
                run_command(['git', 'add', rel_path], SDK_DIR)
                diff_check = run_command(['git', 'status', '--porcelain', rel_path], SDK_DIR)
                
                if diff_check:
                    # 构建 Git Commit Message
                    full_msg = (
                        f"Sync {file_name} from core@{commit_sha}\n\n"
                        f"Original Log: {commit_msg}\n"
                        f"Original Date: {commit_date}"
                    )
                    run_command(['git', 'commit', '-m', full_msg], SDK_DIR)
                    
                    # --- 丰富后的控制台输出 ---
                    print("-" * 60)
                    print(f"✅ 已同步: {rel_path}")
                    print(f"   来源版本: core@{commit_sha}")
                    print(f"   修改内容: {commit_msg}")
                    print(f"   原始时间: {commit_date}")
                    sync_count += 1

    print("-" * 60)
    if sync_count == 0:
        print("✨ 所有组件已是最新，无需同步。")
    else:
        print(f"🚀 同步完成，本次共更新 {sync_count} 个组件。")

if __name__ == "__main__":
    if os.path.exists(SDK_DIR) and os.path.exists(CORE_DIR):
        sync_formulae()