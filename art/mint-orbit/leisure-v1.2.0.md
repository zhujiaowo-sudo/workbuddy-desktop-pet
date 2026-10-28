# 坐姿休闲动画源图与提示词

原角色 Buddy娘，CC-BY-4.0；本项目在原有薄荷坐姿打字图的身份/画风基础上使用内置 imagegen 生成派生姿势，无 CLI/API 回退。继续保留署名及许可，不能作为 CC0 模板分发。

源图：[手机](phone-sheet-v1.2.0.png)、[零食](snack-sheet-v1.2.0.png)。两图均为 4×2 透明网格，实际尺寸以文件为准。提取后固定身体、椅子、外轮廓与脚底，只将面部/前臂区域注册到基准帧；8 帧×200ms，256/512px，运行时平滑插值。没有把“站着的人物+悬浮道具”当成新坐姿。

手机最终提示词：

```text
Create a production 4 columns by 2 rows transparent animation sprite sheet for THIS EXACT mint-green-haired chibi girl from reference (white cat-ear spacesuit hood, mint headphones and trim, emerald eyes, tiny mint boots). NEW ACTION: sitting on a small mint rounded chair, relaxed knees bent, feet resting, playing on a smartphone held naturally by both hands in front of chest. Camera fixed front three-quarter view. Phone SCREEN FACES HER eyes, away from viewer; viewer sees mint phone BACK and small camera dots, never a front-facing black screen. Eyes look down toward her phone. Preserve identity, lineart, pastel shading, proportions. NO computer, NO desk. Eight sequential keyframes: eyes attentive, slow blink, tiny left-thumb tap, right-thumb scroll, soft amused smile, blink, small thumb tap, relaxed attentive again. Every cell exact same camera scale, chair position, feet position, hood outer silhouette, phone placement. Animate only eyebrows/eyelids/thumbs/mouth subtly. Body must NEVER bob or jump. Entire girl/chair/boots fit inside each cell with generous 12% transparent padding on all four sides, identical baseline, no touching adjacent cells. Clean genuinely transparent background, no text, no grid, no ground shadow, no stray pixels. Exactly eight equal rectangular cells 4 by 2, all eight contain full uncut girl seated using her phone.
```

零食最终提示词：

```text
Production transparent animated desktop pet spritesheet, EXACTLY 4 columns x 2 rows equal cells, all eight complete full-body images. Preserve the exact mint chibi girl identity from reference: short mint hair, emerald eyes, white cat-ear helmet hood with mint headphones/trim, white-mint spacesuit, tiny mint boots. NEW ACTION eating snacks naturally while seated comfortably in small mint armchair, knees bent, boots on floor. No computer, no desk. Left hand holds a small yellow snack bowl on lap; right hand picks a small round cracker, brings it toward mouth, takes tiny bite, lowers hand. Anatomically believable, exactly two arms and two hands, snack always connected to hand near mouth; no floating snacks. Eight subtle sequential poses: holding cracker just below lips, brings to lips, nibble happy closed eyes, chewing with hand lowered a little, content smile, raises next cracker a little, small bite, returns relaxed near-mouth pose. Fixed camera front-three-quarter, identical hood contour, chair placement, feet and full body scale EVERY frame. Only local face and right forearm/hand change, no bouncing. Keep ample 12% transparent padding inside every cell; full hood ears/chair/feet uncut, no objects touching cell borders. Soft pastel crisp lineart matching reference. Real transparent background, no lettering, no panel frames, no shadow, no detached speckles.
```
