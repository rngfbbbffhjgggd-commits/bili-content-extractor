---
title: 常见问题
layout: default
---

# ❓ 常见问题

遇到问题先看这里。如果这里没有，欢迎到 [GitHub 仓库](https://github.com/rngfbbbffhjgggd-commits/bili-content-extractor) 提 Issue。

## 💬 B 站相关

**Q：为什么一直提示 cookie 过期 / 需要登录态？**
A：B 站 AI 字幕列表需要登录态。重新按 [使用教程](/bili-content-extractor/usage) 第一步的步骤复制一份新的 `cookie.txt`。cookie 大约一个月过期。

**Q：cookie 会上传吗？安全吗？**
A：不会。cookie 只存在本地文件，只用于调用你本机发起的 B 站接口请求。

## 🔧 环境 / 报错

**Q：提示找不到 `ffmpeg`？**
A：安装 ffmpeg 并把它的目录加到系统 PATH，重启命令行再试。见 [安装](/bili-content-extractor/install)。

**Q：提示模型路径找不到？**
A：确认模型已下载且路径正确。默认根目录是 `D:\BiliModels`，如果模型放在别的盘，用环境变量 `BILI_MODELS_ROOT` 指定。

**Q：`pip install` 很慢 / 失败？**
A：用国内镜像源：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

**Q：模型下载太慢？**
A：用仓库自带的并行下载器（详见 [模型下载](/bili-content-extractor/models)）：
```bash
python parallel_download.py <url> <保存路径> 16 2
```

## 🎤 转写 / 引擎

**Q：Fun-ASR-Nano 出现复读 / 退化？**
A：请确认用的是 **fp16** 版模型。int8 版有已知的复读退化 bug（[sherpa-onnx issue #3062](https://github.com/k2-fsa/sherpa-onnx/issues/3062)）。

**Q：要不要所有模型都下载？**
A：不用。按你常处理的视频类型下对应模型即可。见 [模型下载](/bili-content-extractor/models) 里的选择表。

**Q：怎么强制用某个引擎 / 语言？**
A：加参数即可，例如 `--lang=en --engine=funasr`。完整参数见 [使用教程](/bili-content-extractor/usage)。

## ✨ 总结

**Q：想免费总结，需要 API key 吗？**
A：不需要。用 `投喂DeepSeek网页版.md` 拖进 [chat.deepseek.com](https://chat.deepseek.com) 即可，完全免费。只有加 `--api` 参数才会走 API 并消耗 token。
