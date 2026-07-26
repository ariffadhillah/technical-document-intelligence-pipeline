# Final Delivery Stage Integration

Copy the files into the repository:

```powershell
Copy-Item .\main.py E:\Scraping\test\technical-rag-pipeline\main.py -Force

Copy-Item `
  .\src\processors\final_delivery_stage.py `
  E:\Scraping\test\technical-rag-pipeline\src\processors\final_delivery_stage.py `
  -Force
```

The `final_delivery_exports.txt` file contains optional exports for
`src/processors/__init__.py`. They are not required because `main.py`
imports the stage directly.

Compile:

```powershell
cd E:\Scraping\test\technical-rag-pipeline
py -m compileall main.py src
```

Run the final end-to-end test:

```powershell
py main.py --provider openai --ai-thread-id 3891
```

Expected final log:

```text
[OK] Rendered outputs created
[OK] RAG chunks created
[OK] Final delivery package created
Final folder: ...\output\final\thread_3891
Final ZIP   : ...\output\final\thread_3891_final_delivery.zip
```

Expected output:

```text
output/final/thread_3891/
├── README.md
├── documents/
├── catalogs/
├── reports/
├── rag/
└── logbooks/
```
