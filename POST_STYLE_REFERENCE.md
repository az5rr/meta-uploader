# Feed Post Style Reference

This file is the canonical reference for Arabic feed post rendering and reupload recovery.

## Required Visual Settings

- Canvas size: 1080x1080
- Background color: #EDE3D2
- Primary text color: #111111
- Subtitle/caption color: #6A6A6A
- Arabic font: Amiri
- Arabic text alignment: centered
- Layout: minimal, centered, uncluttered

## Required Content Rules

- Arabic text must be rendered from exact stored Unicode text.
- Arabic shaping and tashkeel must be preserved.
- Do not place English translation text inside the image unless explicitly requested.
- Default feed post image should stay minimal and Arabic-only.
- The written post caption belongs in the Instagram caption area under the post, before the hashtags.
- No logos, usernames, or branding inside the post image.

## Reupload Recovery Rule

If a post must be regenerated:

1. Regenerate the PNG from `arabic_post_generator/`.
2. Verify the Arabic shaping visually.
3. Verify the image remains Arabic-only unless the user explicitly requested an in-image subtitle.
4. Upload only the corrected PNG.

## Current Approved Example

- Arabic text: فَإِنَّ مَعَ الْعُسْرِ يُسْرًا
- Post caption text: place it under the post before hashtags, not inside the image.
