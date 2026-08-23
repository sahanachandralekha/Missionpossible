import React from 'react';
import { ShieldCheck, AlertTriangle, AlertOctagon, ShieldAlert } from 'lucide-react';
import type { RiskLevel } from '../api/types';


interface RiskBadgeProps {
  level: RiskLevel;
  className?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, className = '' }) => {
  const getBadgeDetails = () => {
    switch (level?.toLowerCase()) {
      case 'critical':
        return {
          label: 'CRITICAL RISK',
          icon: <AlertOctagon size={16} aria-hidden="true" />,
          cssClass: 'risk-critical',
        };
      case 'high':
        return {
          label: 'HIGH RISK',
          icon: <ShieldAlert size={16} aria-hidden="true" />,
          cssClass: 'risk-high',
        };
      case 'medium':
        return {
          label: 'MEDIUM RISK',
          icon: <AlertTriangle size={16} aria-hidden="true" />,
          cssClass: 'risk-medium',
        };
      case 'low':
      default:
        return {
          label: 'LOW RISK',
          icon: <ShieldCheck size={16} aria-hidden="true" />,
          cssClass: 'risk-low',
        };
    }
  };

  const { label, icon, cssClass } = getBadgeDetails();

  return (
    <span
      className={`risk-level-badge ${cssClass} ${className}`}
      role="status"
      aria-label={`Risk level assessment: ${label}`}
    >
      {icon}
      <span>{label}</span>
    </span>
  );
};
