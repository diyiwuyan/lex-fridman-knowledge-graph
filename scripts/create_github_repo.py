"""
通过 GitHub API 创建仓库
需要 GitHub Personal Access Token
"""
import subprocess
import json
import sys
import os

# 检查是否有 token
token = os.environ.get("GITHUB_TOKEN", "")
if not token:
    print("请设置 GITHUB_TOKEN 环境变量")
    print("在 GitHub Settings > Developer settings > Personal access tokens 创建")
    sys.exit(1)

import urllib.request
import urllib.error

# 创建仓库
repo_name = "lex-fridman-knowledge-graph"
data = json.dumps({
    "name": repo_name,
    "description": "Lex Fridman Podcast Knowledge Graph - 434 episodes, searchable by guest, topic, and keywords",
    "private": False,
    "auto_init": False
}).encode()

req = urllib.request.Request(
    "https://api.github.com/user/repos",
    data=data,
    headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "Python"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        print(f"✅ 仓库创建成功: {result['html_url']}")
        print(f"   Clone URL: {result['clone_url']}")
except urllib.error.HTTPError as e:
    body = json.loads(e.read())
    if "already exists" in body.get("message", ""):
        print(f"ℹ️  仓库已存在: https://github.com/diyiwuyan/{repo_name}")
    else:
        print(f"❌ 创建失败: {body}")
        sys.exit(1)
