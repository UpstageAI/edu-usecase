import { useState, useEffect, useMemo } from 'react';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Chip } from '../components/Chip';
import { Skeleton } from '../components/Skeleton';
import { ProgressBar } from '../components/ProgressBar';
import { Accordion } from '../components/Accordion';
import { getReport } from '../lib/api';
import { navigate } from '../router';
import './ReportPage.css';


async function fetchReportPdf() {
  const response = await fetch('/mock/result.pdf');
  if (!response.ok) {
    throw new Error('보고서 PDF를 불러오지 못했습니다.');
  }
  return response.blob();
}

export function ReportPage({ proposalId, globalState }) {
  const { state, setReport, openChat, setProposals } = globalState;
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(false);
  
  const report = state.reports[proposalId];
  const proposals = state.proposals || [];
  const proposalCountLabel = useMemo(() => {
    const count = proposals.length;
    if (count === 0) return '제안서 목록';
    return `제안서 ${count}개`;
  }, [proposals]);
  
  useEffect(() => {
    if (!report) {
      loadReport();
    } else {
      setLoading(false);
    }
  }, [proposalId]);

  useEffect(() => {
    if (!report) return;

    setProposals((prevProposals) => {
      const existing = prevProposals.find((item) => item.proposalId === proposalId);

      if (!existing) {
        return [...prevProposals, { proposalId, companyName: report.companyName }];
      }

      if (existing.companyName !== report.companyName) {
        return prevProposals.map((item) =>
          item.proposalId === proposalId
            ? { ...item, companyName: report.companyName }
            : item
        );
      }

      return prevProposals;
    });
  }, [report, proposalId, setProposals]);
  
  const loadReport = async () => {
    setLoading(true);
    setProgress(0);
    setError(null);
    
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
      const data = await getReport(proposalId);
      setReport(proposalId, data);
      setLoading(false);
    } catch (err) {
      console.error('보고서 로드 실패:', err);
      setError('보고서를 불러올 수 없습니다.');
      setLoading(false);
      clearInterval(interval);
    }
  };
  
  const handleDownload = async () => {
    if (!report || downloading) return;

    setDownloading(true);

    try {
      const blob = await fetchReportPdf();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const companyName = report.companyName.replace(/\s+/g, '_');
      link.download = `${companyName}_평가보고서.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('보고서 다운로드 실패:', err);
      alert(err.message || '보고서를 다운로드할 수 없습니다.');
    } finally {
      setDownloading(false);
    }
  };

  const handleNavigateProposal = (nextProposalId) => {
    if (nextProposalId === proposalId) return;
    navigate(`/report/${nextProposalId}`);
  };

  if (loading) {
    return (
      <div className="report-page">
        <ProgressBar progress={progress} />
        <div className="container">
          <div className="report-header-skeleton">
            <Skeleton type="text" width="200px" />
            <Skeleton type="text" width="100px" />
            <Skeleton type="text" width="150px" />
          </div>
          <Skeleton type="box" height="400px" />
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="report-page">
        <div className="container">
          <Card>
            <div className="report-error">
              <p>{error}</p>
              <div className="report-error-actions">
                <Button variant="ghost" onClick={() => navigate('/upload')}>
                  돌아가기
                </Button>
                <Button variant="primary" onClick={loadReport}>
                  다시 시도
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>
    );
  }
  
  if (!report) {
    return (
      <div className="report-page">
        <div className="container">
          <Card>
            <div className="report-error">
              <p>보고서를 찾을 수 없습니다.</p>
              <div className="report-error-actions">
                <Button variant="ghost" onClick={() => navigate('/upload')}>
                  돌아가기
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="report-page fade-in">
      <div className="container">
        <div className="report-header">
          <div className="report-header-top">
            <Button 
              variant="ghost" 
              onClick={() => navigate('/upload')}
            >
              ← 돌아가기
            </Button>
            <div className="report-actions">
              <Button
                variant="primary"
                onClick={handleDownload}
                disabled={downloading}
              >
                {downloading ? '다운로드 중...' : '⬇ 평가 보고서 다운로드'}
              </Button>
              <Button
                variant="ghost"
                onClick={() => openChat(proposalId)}
              >
                💬 질문하기
              </Button>
            </div>
          </div>

          {proposals.length > 0 && (
            <Card
              title={proposalCountLabel}
              className="proposal-collection"
            >
              <div className="proposal-collection-body">
                {proposals.map((item) => {
                  const proposalReport = state.reports[item.proposalId];
                  const isActive = item.proposalId === proposalId;
                  const scoreLabel = proposalReport
                    ? `${proposalReport.totalScore}/${proposalReport.maxScore}점`
                    : '점수 확인';
                  return (
                    <div
                      key={item.proposalId}
                      className={`proposal-item ${isActive ? 'active' : ''}`}
                    >
                      <button
                        type="button"
                        className="proposal-item-main"
                        onClick={() => handleNavigateProposal(item.proposalId)}
                      >
                        <span className="proposal-item-name">
                          {item.companyName || item.proposalId}
                        </span>
                        <span className="proposal-item-meta">{scoreLabel}</span>
                      </button>
                      <Button
                        variant="ghost"
                        size="S"
                        className="proposal-item-chat"
                        onClick={() => openChat(item.proposalId)}
                      >
                        💬
                      </Button>
                    </div>
                  );
                })}
              </div>
            </Card>
          )}
          
          <div className="report-summary">
            <h1>{report.companyName}</h1>
            <div className="report-score-container">
              <div className="report-score">
                <span className="report-score-value">{report.totalScore}</span>
                <span className="report-score-label">/ {report.maxScore}점</span>
              </div>
              <Chip label="평가 완료" status="success" />
            </div>
            <p className="report-created">
              생성일시: {new Date(report.createdAt).toLocaleString('ko-KR')}
            </p>
          </div>
        </div>
        
        {report.highlights && report.highlights.length > 0 && (
          <Card title="주요 강점">
            <ul className="report-list report-highlights">
              {report.highlights.map((item, index) => (
                <li key={index}>✓ {item}</li>
              ))}
            </ul>
          </Card>
        )}
        
        {report.risks && report.risks.length > 0 && (
          <Card title="개선 필요 사항">
            <ul className="report-list report-risks">
              {report.risks.map((item, index) => (
                <li key={index}>⚠ {item}</li>
              ))}
            </ul>
          </Card>
        )}
        
        <Card title="평가 항목별 상세">
          <Accordion items={report.rubricItems} />
        </Card>
      </div>
    </div>
  );
}

