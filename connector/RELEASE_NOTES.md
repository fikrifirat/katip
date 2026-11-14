Katip Kalkan masks Turkish personal data (KVKK) on your computer before Claude reads a document.
Originals and the name map never leave the device.

**Claude Desktop:** download `katip-kalkan.mcpb` below and double-click it (or Settings → Extensions →
Install). You can save the settings as they are: Katip creates `Documents/katip-documents` for your
client files. Ask Claude to "open my Katip folder" to see it in Finder or Explorer. The install
warning appears for every extension installed from a file. To check this download, run
`gh attestation verify katip-kalkan.mcpb --repo fikrifirat/katip`.

**New in 0.3.5 (safety and publishing):**
- Precedent citations stay readable in every profile: "Yargıtay 1. Ceza Dairesi'nin … 2018/123 E., 2019/45 K. sayılı kararı", Danıştay, Anayasa Mahkemesi, BAM/BİM, CGK/HGK. Before, the AI and Tam anonim profiles masked their numbers, dates and court names (lawyer feedback).
- Restored documents (with real names) are written only into your Katip folder, as a real Word file (.docx), .txt or .md. Before, a document could steer Claude into writing them anywhere, and ".docx" got plain text.
- Folder checks work with Windows paths.
- First-start helpers are pinned to exact, tested versions (and Python 3.12 if missing), so an upstream release can't change what runs.
- The plugin starts from `server.py` directly.
- README and privacy policy say what Katip runs, sends and fetches, what it can miss, and that masked text is still personal data under KVKK. Third-party licences are in NOTICE.md.

**New in 0.3.4 (wording):**
- Install text in Turkish and English. It says what Katip does, why Claude Desktop warns, and that the first start takes about a minute.
- Settings in plain words. The threshold setting is removed.
- Permission boxes show which document is being opened ("Belge: … - Vatandaşlık Dava Dilekçesi.udf").
- Errors say what to do next and never suggest pasting client text.
- Claude mentions once that the final text can be saved with the real names on this computer.

**New in 0.3.3:**
- Fixed: files that mention biometric or genetic data (or "sağlık") were refused. The safety check found the word inside its own placeholder ("[BİYOMETRİK/GENETİK-1]") and counted it as a leak. Placeholders are now ignored by the check.

**New in 0.3.2:**
- Fixed: some files were refused with "leak check failed". A passport number, YKN, religion or case number found once is now masked everywhere it appears. Anything still readable is covered automatically before the text goes to Claude.
- An 11-digit number starting with 99, or one written after "T.C. kimlik", "YKN" or "yabancı kimlik", is masked even if its checksum is wrong.
- One language: everything the user sees is in Turkish (or English with the *Language* setting).
- "The file I just added": Claude opens the newest file in the Katip folder.
- `/katip <request>` in Claude Code. In Claude Desktop, *Katip ile güvenli çalış* in the + menu.

**New in 0.3.1:**
- File names stay private: `list_files` hides name-like words, and Claude opens files by id.
- Permission prompts say in Turkish what Katip does.
- The folder setting works with `${HOME}`, and the folder is created for you.
- New `open_folder` tool.

**Claude Code / Cowork:**

    claude plugin marketplace add fikrifirat/katip
    claude plugin install katip-kalkan@katip

Needs Python 3.10+. With [uv](https://docs.astral.sh/uv/) installed, Katip fetches its model runtime
and encryption library on first start; without it, it runs on rules only.

Bundled model: Katip Mask Nano · tr v1.1 (CC BY-SA 4.0, trained partly on Turkish Wiki NER, Altinok 2023). Code: AGPL-3.0, commercial licence on request.
Pre-release for testing with synthetic or public documents. See connector/README.md and DESIGN.md.
