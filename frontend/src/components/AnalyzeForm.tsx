import React, { useState, useRef } from 'react';
import {
  FileText,
  Upload,
  Image,
  File,
  X,
  Sparkles,
  Loader2,
} from 'lucide-react';



interface AnalyzeFormProps {
  isLoading: boolean;
  onAnalyzeText: (text: string) => Promise<void>;
  onAnalyzeFile: (file: File) => Promise<void>;
}

const MAX_TEXT_LENGTH = 100_000;
const ALLOWED_MIME_TYPES = [
  'image/png',
  'image/jpeg',
  'image/jpg',
  'image/webp',
  'application/pdf',
];
const ALLOWED_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp', '.pdf'];

export const AnalyzeForm: React.FC<AnalyzeFormProps> = ({
  isLoading,
  onAnalyzeText,
  onAnalyzeFile,
}) => {
  const [activeTab, setActiveTab] = useState<'text' | 'file'>('text');
  const [textInput, setTextInput] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setClientError(null);

    const trimmed = textInput.trim();
    if (!trimmed) {
      setClientError('Please paste or type opportunity text to analyze.');
      return;
    }

    if (textInput.length > MAX_TEXT_LENGTH) {
      setClientError(`Text exceeds maximum allowed length of ${MAX_TEXT_LENGTH.toLocaleString()} characters.`);
      return;
    }

    await onAnalyzeText(trimmed);
  };

  const handleFileValidationAndSet = (file: File) => {
    setClientError(null);
    if (!file) return;

    if (file.size === 0) {
      setClientError('The selected file is empty (0 bytes).');
      return;
    }

    const fileNameLower = file.name.toLowerCase();
    const hasValidExt = ALLOWED_EXTENSIONS.some((ext) => fileNameLower.endsWith(ext));
    const hasValidMime = ALLOWED_MIME_TYPES.includes(file.type.toLowerCase()) || hasValidExt;

    if (!hasValidExt && !hasValidMime) {
      setClientError('Unsupported file format. Please upload an image (PNG, JPEG, WebP) or PDF document.');
      return;
    }

    const isPdf = fileNameLower.endsWith('.pdf') || file.type === 'application/pdf';
    const maxSize = isPdf ? 15 * 1024 * 1024 : 10 * 1024 * 1024;

    if (file.size > maxSize) {
      const maxMb = isPdf ? 15 : 10;
      setClientError(`File size exceeds maximum permitted limit of ${maxMb} MB.`);
      return;
    }

    setSelectedFile(file);
  };

  const handleFileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setClientError('Please select an image or PDF file to upload.');
      return;
    }
    await onAnalyzeFile(selectedFile);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileValidationAndSet(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const clearFile = () => {
    setSelectedFile(null);
    setClientError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };


  return (
    <div className="form-card">
      <div className="intake-tabs" role="tablist" aria-label="Input Modality">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'text'}
          aria-controls="text-input-panel"
          id="text-tab"
          className={`intake-tab ${activeTab === 'text' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('text');
            setClientError(null);
          }}
        >
          <FileText size={16} aria-hidden="true" />
          <span>Paste Text</span>
        </button>


        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'file'}
          aria-controls="file-upload-panel"
          id="file-tab"
          className={`intake-tab ${activeTab === 'file' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('file');
            setClientError(null);
          }}
        >
          <Upload size={16} aria-hidden="true" />
          <span>Upload Image / PDF</span>
        </button>

      </div>

      {clientError && (
        <div className="error-alert" role="alert">
          <div className="error-message">{clientError}</div>
        </div>
      )}

      {/* TEXT SUBMISSION FORM */}
      {activeTab === 'text' && (
        <form onSubmit={handleTextSubmit} id="text-input-panel" role="tabpanel" aria-labelledby="text-tab">
          <label htmlFor="opportunity-text-input" style={{ display: 'none' }}>
            Opportunity Text
          </label>
          <textarea
            id="opportunity-text-input"
            className="opportunity-textarea"
            placeholder="Paste a job offer, internship message, or recruiter email..."
            value={textInput}
            onChange={(e) => {
              setTextInput(e.target.value);
              if (clientError) setClientError(null);
            }}
            disabled={isLoading}
            maxLength={MAX_TEXT_LENGTH}
            aria-describedby="char-count-info"
          />

          <div className="char-counter" id="char-count-info">
            {textInput.length.toLocaleString('en-US')} / {MAX_TEXT_LENGTH.toLocaleString('en-US')} characters
          </div>

          <button
            type="submit"
            className="submit-btn"
            disabled={isLoading || !textInput.trim()}
            aria-busy={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 size={18} className="spinner" aria-hidden="true" style={{ animation: 'spin 1s linear infinite' }} />
                <span>Analyzing Opportunity...</span>
              </>
            ) : (
              <>
                <Sparkles size={18} aria-hidden="true" />
                <span>Analyze Opportunity</span>
              </>
            )}
          </button>
        </form>
      )}

      {/* FILE SUBMISSION FORM */}
      {activeTab === 'file' && (
        <form onSubmit={handleFileSubmit} id="file-upload-panel" role="tabpanel" aria-labelledby="file-tab">
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            accept=".png,.jpg,.jpeg,.webp,.pdf,image/png,image/jpeg,image/webp,application/pdf"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleFileValidationAndSet(e.target.files[0]);
              }
            }}
            disabled={isLoading}
            id="file-upload-input"
          />

          {!selectedFile ? (
            <div
              className={`dropzone ${isDragging ? 'active' : ''}`}
              onClick={() => fileInputRef.current?.click()}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  fileInputRef.current?.click();
                }
              }}
              aria-label="Upload offer screenshot or PDF document"
            >
              <Upload size={36} className="dropzone-icon" aria-hidden="true" />
              <div className="dropzone-title">Click or Drag & Drop Image or PDF</div>
              <div className="dropzone-subtitle">
                Supports screenshots (PNG, JPG, WebP) and offer letter PDFs (max 15 MB)
              </div>
            </div>
          ) : (
            <div>
              <div className="selected-file-badge">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {selectedFile.name.toLowerCase().endsWith('.pdf') ? (
                    <File size={20} color="#dc2626" aria-hidden="true" />
                  ) : (
                    <Image size={20} color="#2563eb" aria-hidden="true" />
                  )}
                  <span style={{ fontWeight: 500 }}>{selectedFile.name}</span>
                  <span style={{ color: '#64748b', fontSize: '0.8rem' }}>
                    ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)
                  </span>
                </div>
                {!isLoading && (
                  <button
                    type="button"
                    onClick={clearFile}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}
                    aria-label="Remove selected file"
                  >
                    <X size={16} />
                  </button>
                )}
              </div>
            </div>
          )}

          <button
            type="submit"
            className="submit-btn"
            disabled={isLoading || !selectedFile}
            aria-busy={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 size={18} className="spinner" aria-hidden="true" style={{ animation: 'spin 1s linear infinite' }} />
                <span>Analyzing File...</span>
              </>
            ) : (
              <>
                <Sparkles size={18} aria-hidden="true" />
                <span>Analyze Opportunity</span>
              </>
            )}
          </button>
        </form>
      )}
    </div>
  );
};
