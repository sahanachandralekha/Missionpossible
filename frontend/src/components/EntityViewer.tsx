import React, { useState } from 'react';
import { Database, ChevronDown, ChevronUp } from 'lucide-react';
import type { ExtractedEntities } from '../api/types';



interface EntityViewerProps {
  entities?: ExtractedEntities;
}

export const EntityViewer: React.FC<EntityViewerProps> = ({ entities }) => {
  const [isOpen, setIsOpen] = useState<boolean>(false);

  if (!entities) return null;

  const orgs = entities.organizations || [];
  const roles = entities.job_titles || [];
  const emails = entities.contact_emails || [];
  const phones = entities.phone_numbers || [];
  const urls = entities.urls || [];
  const amounts = entities.monetary_amounts || [];
  const locations = entities.locations || [];
  const paymentMethods = entities.payment_methods || [];
  const channels = entities.communication_channels || [];

  const totalCount =
    orgs.length +
    roles.length +
    emails.length +
    phones.length +
    urls.length +
    amounts.length +
    locations.length +
    paymentMethods.length +
    channels.length;

  if (totalCount === 0) return null;

  return (
    <div className="section-box">
      <button
        type="button"
        className="accordion-toggle"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-controls="entities-drawer"
      >
        <span className="section-title" style={{ marginBottom: 0 }}>
          <Database size={16} aria-hidden="true" />
          <span>Extracted Entities ({totalCount} detected)</span>
        </span>
        {isOpen ? <ChevronUp size={18} aria-hidden="true" /> : <ChevronDown size={18} aria-hidden="true" />}
      </button>

      {isOpen && (
        <div id="entities-drawer" style={{ marginTop: '0.75rem' }}>
          <div className="entities-grid">
            {orgs.map((o, idx) => (
              <div key={`org-${idx}`} className="entity-pill">
                <span className="entity-label">Organization</span>
                <span className="entity-value">{o.name}</span>
              </div>
            ))}

            {roles.map((r, idx) => (
              <div key={`role-${idx}`} className="entity-pill">
                <span className="entity-label">Role / Title</span>
                <span className="entity-value">{r.title}</span>
              </div>
            ))}

            {amounts.map((a, idx) => (
              <div key={`amt-${idx}`} className="entity-pill">
                <span className="entity-label">Amount / Fee</span>
                <span className="entity-value">{a.raw_amount}</span>
              </div>
            ))}

            {emails.map((e, idx) => (
              <div key={`email-${idx}`} className="entity-pill">
                <span className="entity-label">Email</span>
                <span className="entity-value">{e.email}</span>
              </div>
            ))}

            {phones.map((p, idx) => (
              <div key={`phone-${idx}`} className="entity-pill">
                <span className="entity-label">Phone</span>
                <span className="entity-value">{p.raw_number}</span>
              </div>
            ))}

            {urls.map((u, idx) => (
              <div key={`url-${idx}`} className="entity-pill">
                <span className="entity-label">Extracted URL</span>
                <span className="entity-value">{u.url}</span>
              </div>
            ))}

            {locations.map((l, idx) => (
              <div key={`loc-${idx}`} className="entity-pill">
                <span className="entity-label">Location</span>
                <span className="entity-value">{l.raw_location}</span>
              </div>
            ))}

            {paymentMethods.map((pm, idx) => (
              <div key={`pm-${idx}`} className="entity-pill">
                <span className="entity-label">Payment Method</span>
                <span className="entity-value">{pm.raw_method}</span>
              </div>
            ))}

            {channels.map((ch, idx) => (
              <div key={`ch-${idx}`} className="entity-pill">
                <span className="entity-label">Channel</span>
                <span className="entity-value">{ch.raw_channel}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
