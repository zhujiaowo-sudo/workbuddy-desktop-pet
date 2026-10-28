# 眨眼与挠头：源图与完整提示词

原角色 Buddy娘，CC-BY-4.0。本次使用内置 imagegen，以原薄荷首帧为身份参考生成待机源图；无 CLI/API 回退。[眨眼源图](idle-sheet-v1.3.0.png)、[挠头源图](scratch-sheet-v1.3.0.png)。保留原许可及改动说明，不属于 CC0 模板。

技术提取按4×2网格、脚底注册；眨眼固定身体与外轮廓、仅合成面部，16帧×200ms，约3.2秒一轮。挠头保留完整上身姿势及抬手路径，固定下身与脚底、替换原放下的手，避免重复手套和局部遮罩裁切头盔；8帧×200ms、非循环。256/512px两档，人物窗口不跳动。PNG透明像素可能保留灰/绿隐藏RGB；按alpha读取，在Qt桌面上无背景，不通过按颜色抠图改变角色。

## 眨眼初稿提示词

```text
Create a production animation sheet for this EXACT Mint Orbit standing chibi girl, preserving her mint bob hair, emerald eyes, white cat-ear helmet with green ear interiors and mint headphones, white/mint belted short tunic skirt, dark green leggings, mint-white boots, tiny gloves. Reference has hidden neon green pixels beneath transparency: ignore all green backdrop fragments, deliver genuinely transparent alpha, no colored background. 4 columns x 2 rows = EIGHT equal cells. In EVERY cell the entire standing girl has identical pose, hood silhouette, feet baseline, scale and camera, arms relaxed. NO body hopping, no drifting, no changing clothes or proportions. Animation only in the facial expression: frame1 eyes open calm; frame2 half close eyelids; frame3 eyes fully closed soft smile; frame4 half open; frame5 eyes open; frame6 tiny relaxed glance to her left without moving head; frame7 eyes return forward; frame8 eyes open soft smile. Entire full body including ears, gloves and boots must fit with 12% transparent margin within every cell, no clipping or cell overlap. Crisp pastel 2D illustrated sprite, soft shading matching reference exactly, clean antialiased edges. No grid, no captions, no symbols, no ground shadow. This is a gentle idle blink sequence, NOT a new character design.
```

## 最终眨眼修订提示词

```text
Fix ONLY the background/alpha of this eight-cell sprite sheet. Preserve every girl's pose, expression, clothing, lineart and 4x2 layout exactly. Remove ALL grey, green, cloudy gradient backdrop and ground shadows between/behind the eight girls. Background must be completely empty transparent alpha=0, NOT gray, checkerboard, green, blur, vignette or translucent haze. Character interiors must be opaque, alpha=255 with antialiasing only at contour edge. Keep eight full uncropped figures, same grid. Export clean transparent PNG sprite cutouts. Do not add scenery, shadows, labels or grids. Transparent background is essential for desktop overlay.
```

## 挠头提示词

```text
Create a NEW EIGHT-frame 4-column x 2-row animation sprite sheet of the exact same mint chibi cat-hood girl in this reference. Same standing body, mint hair/emerald eyes, white cat helmet and headphones, white-mint belted tunic skirt, dark green leggings, mint white boots. New action: a gentle absent-minded HEAD SCRATCH on the OUTSIDE of her helmet near her right temple, as a cute idle thinking gesture; no violent scratching. Frames: 1 both hands relaxed; 2 right elbow bends and glove lifts halfway; 3 right glove reaches outside helmet near temple; 4 tiny back-and-forth rub with eyes half closed; 5 tiny second rub with small amused smile; 6 hand begins lowering; 7 hand halfway down; 8 both arms relaxed again matching frame1. Exactly TWO arms and TWO gloves at all times: when right arm raises the lower original right arm must disappear, never duplicate hands. Anatomically natural elbow motion. Left arm stays relaxed. Feet, waist, torso, head position and hood outline must stay fixed in every cell, no jumping, no changing camera/scale or body pose. The lifted glove may extend slightly past hood side but stays entirely inside its cell. All full-body figures including boots and ears fit with 12% transparent padding. Truly transparent alpha background, no scenery, gray or green backdrop, no floor shadow, no labels, no grid. Preserve identity, soft pastel illustrated style and outfit exactly; animate only right forearm/glove and eyelids/mouth.
```
