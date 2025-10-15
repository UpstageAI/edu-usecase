import { Chip } from './Chip';
import './FileUpload.css';

export function SingleFileUpload({ title, file, onChange }) {
  const handleFileSelect = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      onChange({ name: selectedFile.name });
    }
  };
  
  return (
    <div className="file-upload-section">
      <div className="file-upload-header">
        <h3>{title}</h3>
        {file ? (
          <Chip label="선택됨" status="success" />
        ) : (
          <Chip label="미지정" status="default" />
        )}
      </div>
      <div className="file-upload-body">
        {file ? (
          <div className="file-selected">
            <span className="file-icon">📄</span>
            <span className="file-name">{file.name}</span>
            <button 
              className="file-remove"
              onClick={() => onChange(null)}
            >
              ✕
            </button>
          </div>
        ) : (
          <label className="file-empty">
            <input
              type="file"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
            <span className="file-empty-text">파일을 선택하세요.</span>
            <span className="file-empty-button">파일 선택</span>
          </label>
        )}
      </div>
    </div>
  );
}

