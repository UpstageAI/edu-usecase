import { useRouter } from './router';
import { useGlobalState } from './state';
import { UploadPage } from './pages/UploadPage';
import { ReportPage } from './pages/ReportPage';
import { ChatDrawer } from './components/ChatDrawer';

export function App() {
  const route = useRouter();
  const globalState = useGlobalState();
  const { state, closeChat } = globalState;
  const proposals = state.proposals || [];
  
  const renderPage = () => {
    switch (route.page) {
      case 'upload':
        return <UploadPage globalState={globalState} />;
      case 'report':
        return <ReportPage proposalId={route.proposalId} globalState={globalState} />;
      default:
        return <UploadPage globalState={globalState} />;
    }
  };
  
  // Chat Drawer가 열려있는 경우 해당 보고서 정보 가져오기
  const chatReport = state.ui.chatOpenFor 
    ? state.reports[state.ui.chatOpenFor] 
    : null;
  
  return (
    <>
      {renderPage()}
      {state.ui.chatOpenFor && (
        <ChatDrawer
          isOpen={true}
          onClose={closeChat}
          proposalId={state.ui.chatOpenFor}
          companyName={
            chatReport?.companyName ||
            proposals.find((item) => item.proposalId === state.ui.chatOpenFor)?.companyName ||
            '회사'
          }
          globalState={globalState}
        />
      )}
    </>
  );
}

