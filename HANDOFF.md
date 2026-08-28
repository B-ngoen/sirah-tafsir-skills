
### §15c — Multi-asisten (2026-08-27 malam)
- Repo publik: `docs/{claude,chatgpt,gemini,pi,hermes}.md`; README "Cara pasang" jadi tabel per asisten (+ akurasi ★).
- Gemini web/Gems tidak bisa jalankan lookup.py → paket teks per kitab (`gemini/export_knowledge.py`, penanda `### [src] juz X hal Y | shamela: URL`, ≤25 MB/berkas, ≤10 berkas): rilis `gemini-v1` = gemini-knowledge-tafsir.zip (24,5 MB, 6 txt) + gemini-knowledge-sirah.zip (17,5 MB, 8 txt); instruksi Gem `gemini/instructions-{tafsir,sirah}.md`; README-GEMINI jujur soal retrieval.
- ChatGPT sirah: `chatgpt/sirah/{lookup.py,instructions.md}` (/mnt/data dulu, cache /tmp); README-GPT + bagian sirah & Project; URL tafsir-v1 diperbaiki.
- install.py target pi (~/.pi/agent/skills), hermes (~/.hermes/skills), gemini CLI (~/.gemini/skills). Hermes: `hermes skills install B-ngoen/sirah-tafsir-skills/skills/sirah-lookup` terverifikasi (inspect via skills.sh).
- Belum diuji nyata oleh owner: Gem Knowledge, Custom GPT sirah, hermes install penuh.
