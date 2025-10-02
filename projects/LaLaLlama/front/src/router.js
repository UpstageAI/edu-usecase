import { useState, useEffect } from 'react';

export function useRouter() {
  const [route, setRoute] = useState(parseHash());

  useEffect(() => {
    const handleHashChange = () => {
      setRoute(parseHash());
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  return route;
}

function parseHash() {
  const hash = window.location.hash.slice(1) || '/upload';
  const [path, ...rest] = hash.split('/').filter(Boolean);
  
  if (path === 'upload') {
    return { page: 'upload' };
  }
  
  if (path === 'report' && rest[0]) {
    return { page: 'report', proposalId: rest[0] };
  }
  
  return { page: 'upload' };
}

export function navigate(path) {
  window.location.hash = path;
}

