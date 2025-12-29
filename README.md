# Homebrew No-JDK Tap

[![Sync from Homebrew Core](https://github.com/nojdk/homebrew-nojdk/actions/workflows/sync.yml/badge.svg)](https://github.com/nojdk/homebrew-nojdk/actions/workflows/sync.yml)

这是一个专门为不希望通过 Homebrew 安装 OpenJDK 的开发者设计的 Tap。它会自动同步官方核心库的 Formula，并移除对 `openjdk` 的强制依赖。

## 💡 为什么需要它？

Homebrew 官方库中的许多 Java 工具（如 Maven, Tomcat 等）都强制绑定了 `openjdk`。如果你习惯使用 **SDKMAN!**、**asdf** 或手动管理 Java 版本，Homebrew 的这种做法会导致系统出现冗余的 Java 安装。

本仓库通过自动化脚本，将同步过来的 Formula 中的 `depends_on "openjdk"` 注释掉，从而直接使用你系统中已有的 `java` 环境。

---

## 🚀 快速开始

### 1. 添加 Tap
```bash
brew tap zawn/nojdk
```

### 2. 安装组件


由于官方核心库中存在同名组件，必须使用全路径安装的才是本仓库的无 JDK 版本：
```bash
brew install zawn/nojdk/maven
brew install zawn/nojdk/tomcat
```

---

### 3. 如何验证？
安装完成后，执行以下命令：
```bash
# 检查是否安装了官方 openjdk (预期应为未安装)
brew list openjdk
```
如果看到没有安装openjdk就说明成功了

---

## 🗑️ 卸载与清理

如果你决定不再使用此 Tap，可以按照以下步骤进行彻底清理：

### 1. 卸载通过此 Tap 安装的组件
为了避免残留无效的引用，建议先卸载对应的软件：
```bash
brew uninstall maven
```

### 2. 取消关联 Tap
从本地 Homebrew 环境中移除 `nojdk` 仓库：
```bash
brew untap zawn/nojdk
```

### 3. (可选) 清理缓存
如果需要清理 Homebrew 下载的旧版缓存：
```bash
brew cleanup
```

---

## 🛠 自动化机制

本项目完全由 **GitHub Actions** 驱动，每日自动执行：
1. **同步**：从 `homebrew-core` 获取最新的 `.rb` 文件。
2. **修改**：自动将 `depends_on "openjdk"` 替换为 `# depends_on "openjdk"`。
3. **校验**：仅在内容发生实质逻辑变化时才提交更新。
4. **追溯**：每个 Commit 都会保留官方原始的提交信息和 SHA 记录。

---

## ⚠️ 免责声明

本仓库仅负责移除 `openjdk` 依赖。请确保你的环境变量（如 `JAVA_HOME`）已正确指向你自行安装的 Java 版本，否则相关组件将无法运行。
