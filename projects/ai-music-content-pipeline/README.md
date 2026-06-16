# AI Music Content Pipeline

Automated content pipeline that transforms Spotify track or playlist URLs into a scheduled social media publishing workflow.

## Goal

Build a "Listen-to-Publish" automation system that helps grow a Telegram music channel to 1000+ subscribers by distributing music-related visual content through Pinterest and later Instagram Reels.

## Pipeline

Spotify Track / Playlist URL
→ spotDL
→ MP3 from matched YouTube source
→ metadata and album art
→ synced LRC lyrics
→ JSON manifest
→ AI mood/theme/caption generation
→ Telegram audio post
→ Pinterest visual post
→ archive processed assets

## Local Runtime Structure

~/MusicPipeline/
- inbox/
- lyrics/
- metadata/
- artwork/
- processing/
- sent/
- failed/
- logs/

## Automation Frequency

The agent runs twice weekly.

## Automation Frequency

The agent runs twice weekly.
