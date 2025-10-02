import { useState } from 'react';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Skeleton } from '../components/Skeleton';
import { ProgressBar } from '../components/ProgressBar';
import { SingleFileUpload } from '../components/SingleFileUpload';
import { MultiFileUpload } from '../components/MultiFileUpload';
import { createEvaluation } from '../lib/api';
import { navigate } from '../router';
import './UploadPage.css';

export function UploadPage({ globalState }) {
  const { state, updateState, updateLocalUploads, setProposals } = globalState;
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  
  const handleEvaluationStart = async () => {
    if (!state.localUploads.rfp || !state.localUploads.rubric || state.localUploads.proposals.length === 0) {
      alert('모든 파일을 선택해주세요.');
      return;
    }
    
    setLoading(true);
    setProgress(0);
    
    // 20초 동안 프로그레스 바 애니메이션
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          return 100;
        }
        return prev + 5;
      });
    }, 1000);
    
    try {
      const result = await createEvaluation({
        rfp: state.localUploads.rfp,
        rubric: state.localUploads.rubric,
        proposals: state.localUploads.proposals
      });
      
      updateState({ currentBatchId: result.batchId });
      setProposals(result.proposals || []);
      
      // 첫 번째 제안서로 이동
      if (result.proposals && result.proposals.length > 0) {
        navigate(`/report/${result.proposals[0].proposalId}`);
      }
    } catch (error) {
      console.error('평가 시작 실패:', error);
      alert('평가 시작에 실패했습니다.');
      setLoading(false);
      clearInterval(interval);
    }
  };
  
  const isValid = state.localUploads.rfp && 
                  state.localUploads.rubric && 
                  state.localUploads.proposals.length > 0;
  
  if (loading) {
    return (
      <div className="upload-page">
        <ProgressBar progress={progress} />
        <div className="container">
          <Card title="RFP 업로드">
            <Skeleton type="box" height="120px" />
          </Card>
          <Card title="심사표 업로드">
            <Skeleton type="box" height="120px" />
          </Card>
          <Card title="제안서 업로드">
            <Skeleton type="box" height="200px" />
          </Card>
        </div>
      </div>
    );
  }
  
  return (
    <div className="upload-page">
      <div className="container">
        <div className="page-header">
          <h1>제안서 평가 시스템</h1>
          <p className="page-description">
            RFP, 심사표, 제안서를 업로드하여 AI 기반 평가를 시작하세요.
          </p>
        </div>
        
        <div className="upload-sections">
          <Card className="upload-card">
            <SingleFileUpload
              title="RFP 업로드"
              file={state.localUploads.rfp}
              onChange={(file) => updateLocalUploads({ rfp: file })}
            />
          </Card>
          
          <Card className="upload-card">
            <SingleFileUpload
              title="심사표 업로드"
              file={state.localUploads.rubric}
              onChange={(file) => updateLocalUploads({ rubric: file })}
            />
          </Card>
          
          <Card className="upload-card">
            <MultiFileUpload
              title="제안서 업로드"
              files={state.localUploads.proposals}
              onChange={(files) => updateLocalUploads({ proposals: files })}
            />
          </Card>
        </div>
        
        <div className="upload-footer">
          <div className="upload-summary">
            {isValid ? (
              <>
                <span>✓ RFP 1개</span>
                <span>✓ 심사표 1개</span>
                <span>✓ 제안서 {state.localUploads.proposals.length}개</span>
              </>
            ) : (
              <span className="upload-summary-empty">
                모든 파일을 선택해주세요
              </span>
            )}
          </div>
          <Button
            variant="primary"
            disabled={!isValid}
            onClick={handleEvaluationStart}
          >
            평가 시작
          </Button>
        </div>
      </div>
    </div>
  );
}

