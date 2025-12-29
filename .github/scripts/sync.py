import os
import subprocess
import hashlib

# --- 配置区 ---
BASE_DIR = os.getcwd()
CORE_DIR = os.path.join(BASE_DIR, "homebrew-core")
SDK_DIR = os.path.join(BASE_DIR, "homebrew-sdkman")

TARGET_DEP = 'depends_on "openjdk"'
COMMENTED_DEP = '# depends_on "openjdk"'

def get_logic_hash(content):
    normalized = content.replace(COMMENTED_DEP, TARGET_DEP)
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()

def run_command(command, cwd):
    print(f"      [EXEC]: {' '.join(command)} in {cwd}")
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"      [GIT ERR]: {result.stderr.strip()}")
    return result.stdout.strip() if result.returncode == 0 else None

def sync_formulae():
    search_base = os.path.join(CORE_DIR, "Formula")
    if not os.path.exists(search_base):
        search_base = CORE_DIR

    print(f"🔍 DEBUG: 搜索目录 = {search_base}")
    sync_count = 0

    for root, dirs, files in os.walk(search_base):
        for file_name in files:
            if not file_name.endswith(".rb"):
                continue

            src_file_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(src_file_path, CORE_DIR)
            dst_file_path = os.path.join(SDK_DIR, rel_path)

            # 针对 maven.rb 开启超级追踪
            is_maven = "maven.rb" in file_name
            if is_maven:
                print(f"\n🎯 [TRACE] 正在检查 maven.rb")
                print(f"   源文件路径: {src_file_path}")
                print(f"   目标文件路径: {dst_file_path}")

            try:
                with open(src_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                if is_maven: print(f"   ❌ 读取失败: {e}")
                continue

            if TARGET_DEP in content:
                if is_maven: print(f"   ✅ 发现目标依赖: {TARGET_DEP}")

                if os.path.exists(dst_file_path):
                    with open(dst_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        dst_content = f.read()
                    
                    src_h = get_logic_hash(content)
                    dst_h = get_logic_hash(dst_content)
                    if is_maven:
                        print(f"   对比哈希: SRC({src_h}) vs DST({dst_h})")

                    if src_h == dst_h:
                        if is_maven: print(f"   ⏭️ 内容逻辑一致，跳过")
                        continue

                # 执行修改
                os.makedirs(os.path.dirname(dst_file_path), exist_ok=True)
                new_content = content.replace(TARGET_DEP, COMMENTED_DEP)
                with open(dst_file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                if is_maven: print(f"   ✍️ 已写入修改后的内容到目标路径")

                # Git 流程
                commit_sha = run_command(['git', 'log', '-1', '--format=%h', '--', rel_path], CORE_DIR)
                run_command(['git', 'add', rel_path], SDK_DIR)
                
                # 关键：检查 Status
                diff_check = run_command(['git', 'status', '--porcelain', rel_path], SDK_DIR)
                if is_maven: print(f"   Git Status 输出: '{diff_check}'")

                if diff_check:
                    run_command(['git', 'commit', '-m', f"Sync {file_name} from core"], SDK_DIR)
                    print(f"✅ 已成功提交更新: {rel_path}")
                    sync_count += 1
                elif is_maven:
                    print(f"   ⚠️ Git 认为文件没有变化，未执行提交")

    print(f"\n🚀 同步结束，更新总数: {sync_count}")

if __name__ == "__main__":
    sync_formulae()