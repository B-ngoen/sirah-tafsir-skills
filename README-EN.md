# sirah-tafsir-skills (English)

*Versi Indonesia (utama): [README.md](README.md)*

Skills that let AI assistants (Claude, ChatGPT, and other agents) quote classical **Arabic tafsīr and sīrah sources verbatim** — with printed volume/page citations and Maktabah Shamela links — instead of relying on the model's memory. Free, non-commercial waqf.

| Skill | Status | Sources |
|---|---|---|
| **tafsir-lookup** | ✅ ready | Tafsīr al-Ṭabarī · al-Marāghī · Ṣafwat al-Tafāsīr (al-Ṣābūnī) · Ibn Kathīr (2 editions) — 6,236/6,236 verses |
| **sirah-lookup** | ✅ ready | Ibn Hishām (2 eds.) · Ibn Isḥāq · Ṭabaqāt Ibn Saʿd · Tārīkh al-Ṭabarī · al-Iṣābah · Usd al-Ghābah (2 eds.) · al-Istīʿāb — 175 events/years & ~9,700 Companions |

## Install

**One sentence (Claude Code, Codex, any agent with a terminal):**
> Please study https://github.com/B-ngoen/sirah-tafsir-skills and install it as a skill.

The agent follows [INSTALL.md](INSTALL.md), runs the installer (`python install.py`, no git needed), downloads the database once (~18 MB), and you simply ask, e.g. "Tafsīr of Q 2:255 according to al-Ṭabarī, Arabic text with page citation."

**claude.ai / Claude apps:** download `tafsir-lookup.skill` ([tafsir-v1](https://github.com/B-ngoen/sirah-tafsir-skills/releases/tag/tafsir-v1)) and/or `sirah-lookup.skill` ([sirah-v1](https://github.com/B-ngoen/sirah-tafsir-skills/releases/tag/sirah-v1)) → Settings → Capabilities → Skills → Upload. The database downloads automatically inside Claude's sandbox on first use.

**ChatGPT:** use the published Custom GPT (link to be added), or build your own in ~5 minutes with [chatgpt/README-GPT.md](chatgpt/README-GPT.md) (paste `instructions.md`, upload `lookup.py` + `tafsir_full.db.xz`, enable Code Interpreter).

**Other agents:** paste `skills/tafsir-lookup/SKILL.md` into the agent instructions and run `python skills/tafsir-lookup/scripts/lookup.py 2:255`.

## Principles
Verbatim text · mandatory citation (book, edition, volume/page, URL) · absent sources are reported absent · AI paraphrase always labelled · two modes (concise reference vs. full study material read chapter by chapter).

## Sources, attribution, licence
Texts from **Maktabah Shamela (shamela.ws)**, fetched page by page (tafsīr 18 Aug 2026, sīrah 26 Aug 2026) with the printed volume/page numbers of the editions Shamela uses. Classical texts are public domain; editors' footnotes are kept for fidelity — rights holders who object may open an Issue and the material will be removed in the next release. The public edition excludes modern copyrighted works (e.g. Dorar EN). Code: MIT. Database: non-commercial waqf, not for sale.

## Known limitations
Ṣafwat al-Tafāsīr electronic edition is truncated (sūrah 114 missing); Ibn Kathīr (Ibn al-Jawzī ed.) truncated at the end (113–114 only a joint introduction). Segment boundaries come from headings (rules + LLM); range labels are explained in the output. Sīrah: event registry still a draft (corrections welcome); Ibn Hishām (Ṭāhā ed.) electronic edition truncated at Badr (flagged); cross-dictionary Companion links ~78 % (status stored per entry).
