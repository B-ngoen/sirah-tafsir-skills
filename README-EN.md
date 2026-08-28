# sirah-tafsir-skills (English)

*Versi Indonesia (utama): [README.md](README.md)*

Skills that let AI assistants (Claude, ChatGPT, and other agents) quote classical **Arabic tafsīr and sīrah sources verbatim** — with printed volume/page citations and Maktabah Shamela links — instead of relying on the model's memory. Free, non-commercial waqf.

| Skill | Status | Sources |
|---|---|---|
| **tafsir-lookup** | ✅ ready | Tafsīr al-Ṭabarī · al-Marāghī · Ṣafwat al-Tafāsīr (al-Ṣābūnī) · Ibn Kathīr (2 editions) — 6,236/6,236 verses |
| **sirah-lookup** | ✅ ready | Ibn Hishām (2 eds.) · Ibn Isḥāq · Ṭabaqāt Ibn Saʿd · Tārīkh al-Ṭabarī · al-Iṣābah · Usd al-Ghābah (2 eds.) · al-Istīʿāb — 175 events/years & ~9,700 Companions |

## Install — pick your assistant

| Assistant | What to do | Accuracy | Guide (ID) |
|---|---|---|---|
| **Claude** claude.ai / desktop app (free tier works); **set up on a PC**, then use it on mobile too | On a PC: download [tafsir-lookup.skill](https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/release/tafsir-lookup.skill) and/or [sirah-lookup.skill](https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/release/sirah-lookup.skill) → Settings → Capabilities → Skills → Upload. The database downloads automatically on Claude's side on first use — same on phone or desktop. | ★★★ reads the database directly | [docs/claude.md](docs/claude.md) |
| **Claude Code** (terminal) | Paste: *"Please study https://github.com/B-ngoen/sirah-tafsir-skills and install it as a skill."* | ★★★ | [docs/claude.md](docs/claude.md) |
| **ChatGPT** web / desktop app (Plus/Team); **set up on a PC**, the Project then appears on mobile too | On a PC: **Work/Projects** → new Project → upload 2 files (lookup script + database) → paste the instructions. | ★★★ | [docs/chatgpt.md](docs/chatgpt.md) |
| **Gemini** via **NotebookLM** (free), optionally a Gem | Upload the plain-text book package to NotebookLM → paste the instructions → ask. For the Gemini app, create a Gem whose source is that notebook. | ★★ text retrieval (long chapters may come back incomplete) | [docs/gemini.md](docs/gemini.md) |
| **Hermes Agent** | `hermes skills install B-ngoen/sirah-tafsir-skills/skills/sirah-lookup` (and `.../tafsir-lookup`) | ★★★ | [docs/hermes.md](docs/hermes.md) |
| **pi**, Codex, Gemini CLI, other terminal agents | Same sentence as Claude Code, or `python install.py --target pi` / `codex` / `gemini` | ★★★ | [docs/pi.md](docs/pi.md) |

Then just ask, e.g. "Tafsīr of Q 2:255 according to al-Ṭabarī, Arabic text with page citation" or "The battle of Badr according to Ibn Hishām, Arabic text".

## Principles
Verbatim text · mandatory citation (book, edition, volume/page, URL) · absent sources are reported absent · AI paraphrase always labelled · two modes (concise reference vs. full study material read chapter by chapter).

## Sources, attribution, licence
Texts from **Maktabah Shamela (shamela.ws)**, fetched page by page (tafsīr 18 Aug 2026, sīrah 26 Aug 2026) with the printed volume/page numbers of the editions Shamela uses. Classical texts are public domain; editors' footnotes are kept for fidelity — rights holders who object may open an Issue and the material will be removed in the next release. Code: MIT. Database: non-commercial waqf, not for sale.

## Known limitations
Ṣafwat al-Tafāsīr electronic edition is truncated (sūrah 114 missing); Ibn Kathīr (Ibn al-Jawzī ed.) truncated at the end (113–114 only a joint introduction). Segment boundaries come from headings (rules + LLM); range labels are explained in the output. Sīrah: event registry still a draft (corrections welcome); Ibn Hishām (Ṭāhā ed.) electronic edition truncated at Badr (flagged); cross-dictionary Companion links ~78 % (status stored per entry).
