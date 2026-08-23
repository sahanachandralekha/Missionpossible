import React, { useState } from 'react';
import { ChevronDown, ChevronUp, FileText } from 'lucide-react';
import type { Evidence } from '../api/types';


interface EvidenceViewerProps {
  evidence: Evidence[];
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({ evidence }) => {
  const [isOpen, setIsOpen] = useState<boolean>(false);

  if (!evidence || evidence.length === 0) return null;

  return (
    <div className="section-box">
      <button
        type="button"
        className="accordion-toggle"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-controls="evidence-drawer"
      >
        <span className="section-title" style={{ marginBottom: 0 }}>
          <FileText size={16} aria-hidden="true" />
          <span>Supporting Evidence ({evidence.length} items)</span>
        </span>
        {isOpen ? <ChevronUp size={18} aria-hidden="true" /> : <ChevronDown size={18} aria-hidden="true" />}
      </button>

      {isOpen && (
        <div id="evidence-drawer" className="evidence-drawer">
          {evidence.map((item, idx) => (
            <div key={`evidence-${idx}`} className="evidence-item">
              <div>
                <strong>[{item.type || 'EXCERPT'}]</strong> <em>({item.source || 'text'})</em>
                {item.location && <span> • Location: {item.location}</span>}
              </div>
              <div style={{ marginTop: '0.25rem', color: '#f8fafc' }}>
                "{item.value}"
              </div>
              {item.context && item.context !== item.value && (
                <div style={{ marginTop: '0.2rem', color: '#94a3b8', fontSize: '0.75rem' }}>
                  Context: "{item.context}"
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
