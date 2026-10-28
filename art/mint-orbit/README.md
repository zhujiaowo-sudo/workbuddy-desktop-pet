# 薄荷星伴坐姿打字素材

原角色作者：Buddy娘。原素材版本1.0.1，CC-BY-4.0，来源见根目录NOTICE.md。此处为本项目使用内置`imagegen`生成的派生工作姿势，继续注明原角色和改动；不属于CC0机器人模板。用户提供的另一张图仅作为坐姿桌椅构图参考，没有分发该参考图或其中角色。

[typing-sheet-v1.1.1.png](typing-sheet-v1.1.1.png)是最终选用的4列×2行透明源图。第一轮4×4方案存在底部裁切，未纳入项目；第二轮要求完整脚部/桌椅和透明留边。实际生成尺寸由图像文件决定，提取工具按相对网格定位，不将提示词中的理想尺寸视为实际分辨率。

`sprite_sheet.py`负责技术处理：去除孤立杂点、统一缩放、按桌脚与底部注册，锁定桌椅和人物外轮廓，仅合成面部及手部局部关键帧，导出8帧×160ms的256/512px画布。播放器在运行时做平滑插值；没有增加源素材帧数。新版完整包仍为15段。

## 最终生成提示词（内置工具，无CLI/API回退）

```text
Polish the supplied Mint Orbit seated typing sprite sheet into a new EIGHT-FRAME desktop-pet animation sheet. Preserve the same mint-haired chibi cat-hood astronaut girl and the same attractive seated-at-a-desk computer composition. Critical correction: the current sheet clips feet and chair/table legs at cell boundaries. Give EVERY sprite generous transparent padding on ALL FOUR sides. Produce a WIDE 2:1 transparent canvas, ideally 2048x1024 pixels, exact FOUR columns and TWO rows = eight equal square frames. NO borders/grid lines/captions/text. Each character-and-desk sprite must fit fully within only the central 78% of its cell, with at least 10% transparent padding at left/right/top/bottom. Every chair foot, every table foot and her entire shoes MUST be visible, fully contained, never touching a cell edge. Absolutely no clipping or cross-cell overlap. Remove detached white/green edge speckles and keep clean polished antialiased alpha. SAME FIXED sprite placement, same head shape and body proportions, same camera and desk/chair/monitor geometry in all eight cells. Her monitor is on the RIGHT, display surface points LEFT TOWARD HER FACE; viewer sees its grey-blue BACK and side, never the lit screen. Girl is genuinely SITTING on mint stool/chair behind a cream-and-light-wood desk, feet naturally supported below, both hands at keyboard in front of her. Animate only tiny alternating typing hand/finger movement and a soft blink in two frames, with a concentrated pleasant expression. No whole-body up/down movement, no jumping, no head translation, no shifting desk, no changing camera angle. This is an animation production asset: identity and fixed environment must be extremely consistent across all eight frames. Transparent RGBA, no floor, no red/white/black background. Keep mint/white/blue color palette and original charming illustration style.
```

该轮输入为第一轮薄荷坐姿草稿；初轮输入为项目默认薄荷首帧和用户坐姿构图参考。生成后使用相同图像技术提取，没有把原参考人物复制进包内。
