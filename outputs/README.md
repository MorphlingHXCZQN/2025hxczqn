# Outputs Directory

This folder collects generated artefacts such as Word exports, PDF downloads, and
article summaries produced by the automation scripts. The directory is ignored by
Git (see `.gitignore`), ensuring binary files never block repository updates.

Typical files created here include:

- `serum_tdp43_sepsis_project.docx`: Word export of the project plan.
- `literature_summaries/`: Machine-readable JSON/Markdown notes for each article.

To rebuild the artefacts, run the literature pipeline:

```bash
python tools/literature_pipeline.py --cache data/cached_serum_tdp43_sepsis_crossref.json \
    --rows 12 --offline
```

The command will default to `outputs/` for all downloads and exports, keeping the
repository clean while still letting you regenerate everything locally. When you
are ready to commit, run `python tools/cleanup_workspace.py` to wipe this folder
and other ignored caches so no binary artefacts remain.
