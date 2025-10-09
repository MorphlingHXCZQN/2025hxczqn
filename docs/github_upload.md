# GitHub 上传指南

本文档帮助您将当前项目上传到个人 GitHub 仓库。由于本环境无法直接访问外部网络，请在本地机器执行以下步骤。

## 1. 准备工作

1. 在本地创建一个空目录，例如 `esophageal-imaging-pipeline`。
2. 将当前项目文件复制到该目录，可通过 `scp`、`zip`、`git clone` 等方式将容器中的仓库同步到本地。
3. 安装 Git（Windows 可通过 [Git for Windows](https://git-scm.com/download/win)）。

## 2. 初始化本地仓库

```bash
cd esophageal-imaging-pipeline
git init
```

如需保留现有提交历史，可使用 `git clone` 获取整个仓库；若仅复制文件，执行 `git init` 即可。

## 3. 配置远程仓库

1. 登录 GitHub，点击右上角 **New repository** 创建一个新的仓库，例如 `esophageal-imaging-pipeline`。
2. 复制 GitHub 提供的远程地址，例如：
   - HTTPS: `https://github.com/<username>/esophageal-imaging-pipeline.git`
   - SSH: `git@github.com:<username>/esophageal-imaging-pipeline.git`
3. 在本地仓库中添加远程：

   ```bash
   git remote add origin <remote-url>
   ```

## 4. 提交与推送

```bash
git add .
git commit -m "Initial commit: offline esophageal imaging pipeline"
git branch -M main
git push -u origin main
```

若仓库已存在历史提交，请先执行 `git pull --rebase origin main` 合并远程更新，再推送。

### 4.1 通过 Pull Request 上传

如果您希望以 Pull Request（PR）的方式上传更新，可以按以下步骤操作：

1. 为本次变更创建新分支，例如：

   ```bash
   git checkout -b feature/add-docx-export
   ```

2. 在该分支上提交修改后推送到远程：

   ```bash
   git push -u origin feature/add-docx-export
   ```

3. 打开 GitHub 仓库页面，点击 **Compare & pull request**，填写 PR 标题与说明（可复用本仓库 `docs/` 与 `README.md` 中的结构），然后提交 PR。
4. 审查通过并合并后，主分支即可获得最新变更；如需保留记录，可选择 **Merge commit** 或 **Squash & merge**。

创建 PR 并不会自动限制您上传文件，只要拥有仓库的推送权限，即可通过分支推送或直接推送到主分支。

## 5. 验证

1. 在浏览器中打开 GitHub 仓库，确认文件已同步；
2. 检查 `D/计划` 目录是否符合预期，如需要避免提交真实大数据，可在 `.gitignore` 中添加对应路径。

## 6. 后续协作建议

- 使用 `git pull`/`git push` 保持本地与远程同步；
- 创建功能分支（如 `feature/real-pubmed-client`）开发新能力；
- 借助 Pull Request 审阅代码和文档更新；
- 在 `docs/` 目录中持续记录检索策略、数据处理与研究方案。

如需进一步自动化发布，可结合 GitHub Actions 在推送后触发测试，确保离线管线在 CI 环境中稳定运行。
