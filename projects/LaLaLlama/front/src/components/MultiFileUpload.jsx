import { Chip } from './Chip';
import './FileUpload.css';

export function MultiFileUpload({ title, files, onChange }) {
  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files || []);
    const newFiles = selectedFiles.map((file, index) => ({
      name: file.name,
      tempId: `${Date.now()}-${index}`
    }));
    onChange([...files, ...newFiles]);
  };
  
  const removeFile = (tempId) => {
    onChange(files.filter(f => f.tempId !== tempId));
  };
  
  return (
    <div className="file-upload-section">
      <div className="file-upload-header">
        <h3>{title}</h3>
        {files.length > 0 ? (
          <Chip label={`${files.length}개 선택됨`} status="success" />
        ) : (
          <Chip label="미지정" status="default" />
        )}
      </div>
      <div className="file-upload-body">
        {files.length > 0 ? (
          <div className="file-list">
            {files.map(file => (
              <div key={file.tempId} className="file-item">
                <span className="file-icon">📄</span>
                <span className="file-name">{file.name}</span>
                <button 
                  className="file-remove"
                  onClick={() => removeFile(file.tempId)}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="file-empty-text">파일을 선택하세요.</div>
        )}
        <label className="file-add-button">
          <input
            type="file"
            multiple
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          파일 추가
        </label>
      </div>
      <div className="file-upload-caption">제안서는 최대 20개까지 업로드해 주세요.</div>
    </div>
  );
}

