# Models Directory

This directory contains machine learning models used by the document converter.

## PaddleOCR Models

The `paddle_models/` subdirectory contains PaddleOCR models that are automatically downloaded when the application first runs OCR functionality.

### Model Files

When OCR is first used, the following models will be downloaded:

- **PP-OCRv5_server_det**: Text detection model
- **PP-OCRv5_server_rec**: Text recognition model  
- **PP-LCNet_x1_0_doc_ori**: Document orientation classifier
- **PP-LCNet_x1_0_textline_ori**: Text line orientation classifier
- **UVDoc**: Document rectification model

### Storage Location

Models are automatically stored in: `./models/paddle_models/`

The application automatically:
1. Downloads models to the system default location on first run
2. Copies models to the project directory for persistence
3. Uses local models on subsequent runs (no re-download)

### Model Management

- **First Run**: Models are downloaded and copied to project (~210MB total)
- **Subsequent Runs**: Models are loaded from project directory (instant startup)
- **Updates**: Delete the `./models/paddle_models/` directory to force re-download
- **Cleanup**: Models can be safely deleted to free disk space (will re-download automatically)
- **Backup**: The entire `models/` directory can be backed up or shared between deployments

### Directory Structure

```
models/
└── paddle_models/
    ├── PP-OCRv5_server_det/       # Text detection model
    │   ├── inference.pdiparams    # Model parameters (~47MB)
    │   ├── inference.pdiparams.info
    │   ├── config.json            # Model configuration
    │   └── ...
    ├── PP-OCRv5_server_rec/       # Text recognition model
    │   ├── inference.pdiparams    # Model parameters (~31MB)
    │   ├── inference.pdiparams.info
    │   ├── config.json
    │   └── ...
    ├── PP-LCNet_x1_0_doc_ori/     # Document orientation (~44MB)
    ├── PP-LCNet_x1_0_textline_ori/ # Text line orientation (~44MB)
    ├── UVDoc/                     # Document rectification (~53MB)
    └── ...
```

**Total Storage**: ~210MB across 65 files in 5 model directories

### Customization

To use different models or languages:

1. Update `PADDLE_OCR_LANG` in your `.env` file
2. Delete the existing `paddle_models/` directory
3. Restart the application to download new models

### Troubleshooting

If models fail to load:

1. Check disk space (~500MB required)
2. Verify internet connection for initial download
3. Check file permissions on models directory
4. Delete and re-download models if corrupted

## Notes

- Models are shared across all application instances
- The directory is automatically created on first run
- Models are excluded from version control (see `.gitignore`)
- Total storage: ~200-500MB depending on language packs