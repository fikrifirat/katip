Katip Kalkan masks Turkish personal data (KVKK) on your computer before Claude reads a document.
Originals and the name map never leave the device.

**Claude Desktop:** download `katip-kalkan.mcpb` below and double-click it (or Settings → Extensions →
Install). In the settings, pick the folder where you keep your case files; Downloads (UYAP downloads,
e-mail attachments) is searched too. Nothing has to be copied anywhere. The install
warning appears for every extension installed from a file. To check this download, run
`gh attestation verify katip-kalkan.mcpb --repo fikrifirat/katip`.

**New in 0.5.1 (Gazette lookups, from the first lawyer-style test):**
- The Gazette lookup now keeps every notice the site lists, not only the pages Katip reads. Notices whose page was not read are marked "listed, text not read", so a report can no longer present 3 of 10 as all of them.
- When the Gazette site asks for its security code, a Chrome window opens on that page; you type the code, and Katip carries on in the background. Katip never reads or fills the code.
- Every Gazette record carries a citation (TTSG date, issue, page) and how to verify it on ticaretsicil.gov.tr. The answer also says when court notices (konkordato, iflas) were not part of the search.
- A gazette page that holds two of the notices is downloaded once.

**New in 0.5.0 (Katip DD: due-diligence screening, beta):**
- Seven `dd_*` tools screen a person or company against MASAK asset-freeze lists, ilan.gov.tr notices and the Ticaret Sicili Gazetesi, from the same extension. Every hit is the source's own record with its official link and the date of the data; nothing is summarised, and no hit is not a clearance. Other people's ID numbers and parents' names are removed before Claude sees a result; a company's labelled tax number (VKN) stays.
- ilan.gov.tr and the Gazette are looked up one named target at a time in the Google Chrome already on your computer. For the Gazette you log in once with e-Devlet in a Chrome window; the site's cookies are kept encrypted for 8 hours and later lookups run in the background with no window. `dd_gazette_logout` ends it at once. If the site asks for its security code (it did after about 6 searches in our test), Katip stops and does not solve it.
- First start also fetches Playwright (about 40 MB) once with the other helpers. Without Google Chrome, the lookup tools say so and point to the download.
- Tested on a real Mac against the live sites (22 Nov 2026): 17 of 17 ilan.gov.tr notices and 7 of 7 Gazette notices about 10 companies from konkordato news found, no wrong hits, no hits for 6 invented companies. Not yet tried by a lawyer.

**New in 0.4.1 (final documents for UYAP, and a citation check):**
- `restore_to_file` saves the final document with real names as `.udf` (UYAP's document format, written the same way as the UDF test files Katip already reads; not yet opened in UYAP Doküman Editörü by us, so check the first one) or `.pdf`, besides `.docx`, `.txt` and `.md`.
- Every draft saved this way has its statute citations checked first, offline, against Katip's copy of mevzuat.adalet.gov.tr: does the article exist, is it in force, do number and name match. Claude lists any citation that fails before you file the document. Decision citations are not checked here (use precedent search).

**New in 0.4.0 (one engine with the katip-mask SDK):**
- Detection now comes from [katip-mask](https://pypi.org/project/katip-mask/) 0.1.1, the same rules as the Katip app and the SDK, pinned to that exact version: new detection code reaches your computer only through a reviewed Kalkan release. Without uv or offline, Katip uses the same rules bundled in the plugin (a test checks both mask exactly the same).
- New setting **Ad modeli / Name model**: `nano` (bundled, default, no network), `mini` (31 MB) or `base` (110 MB, best name recall on KVKK-Bench). Mini and Base download once from Hugging Face at the commit pinned in katip-mask, every file checked by SHA-256, then work offline; if the download fails Katip keeps using Nano and says so. The first document after switching takes a minute or two. In Claude Code, set `KATIP_MODEL=base` in the shell you start Claude from.
- `katip_status` shows where detection comes from and which model runs.
- CI starts Katip the way you get it, through uv, on Linux, macOS and Windows.

**New in 0.3.8 (documents stay where you keep them):**
- Katip looks in your case folder (with its subfolders) and in Downloads, where UYAP downloads and e-mail attachments land. You no longer copy files into a Katip folder.
- Describe the document the way you'd tell a colleague (`/katip-incele son indirdiğim bilirkişi raporu`, `/katip-taslak 2026/123 ihtarname, cevap`): Katip searches file and folder names on your computer, ignoring Turkish letters and case, and Claude sees only shortened names. If several match, Claude asks which one.
- The final document with real names is saved next to the document you worked on.
- More folders: add them in the settings (Claude Desktop) or one per line in `~/.katip/folders.txt` (Claude Code). The guard in Claude Code covers all of them. `KATIP_DOWNLOADS=0` turns the Downloads search off.

**New in 0.3.7 (court copies and everyday use):**
- Court profile (Mahkemeye sunum): UETS addresses, bar registry numbers and the parties' own addresses are masked; the address of the property in dispute stays readable (lawyer feedback).
- Claude Code and Cowork: a guard stops Claude's own Read, Grep, Glob, Edit, Write and Bash tools from opening the Katip folder or the name map, so client files are opened only through Katip.
- New commands `/katip-incele` (review and summarise) and `/katip-taslak` (draft a reply, save it with real names); in Claude Desktop they are in the + menu.
- Clearer Turkish tool names, and the approval prompt now says that Katip can miss a value and that restored files go only into the Katip folder.
- Claude asks for a matter label only when you work on several documents of one case.
- The listing links the FAQ, the data-processing statement and the KVKK Board's guide for lawyers.

**New in 0.3.6 (names):**
- Finds a lone first or last name inside a sentence when the name model is sure of it, joins names the model returns word by word, and masks a word of a full name found elsewhere in the document when it appears alone (KVKK-Bench, Base: 92.0 → 93.1, leaks 3.3% → 3.1%, no new false alarms on court text).
- Default detection threshold 0.5 (was 0.7), tuned on the dev split, the same rules and threshold as the katip-mask 0.1.0 SDK. Blind set: 748 of 757 values masked.
- Releases now publish themselves when the version in manifest.json changes on main.

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
