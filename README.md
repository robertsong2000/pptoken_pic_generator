# PPToken 图片生成器

通过 PPToken API 生成图片的 Python 脚本。

## 使用方法

1. 安装依赖：

```bash
uv venv && source .venv/bin/activate
uv pip install requests python-dotenv
```

2. 配置 `.env` 文件：

```
PPTOKEN_API_KEY=your_api_key_here
```

3. 生成图片：

```bash
python pic_generator.py "一只可爱的猫咪"
```

不传参数时默认生成"生成一张猫的图"。
