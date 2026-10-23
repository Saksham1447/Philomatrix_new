import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { formatIndianDateTime } from '../utils/time';
import { AuditLog } from '../types';
import { ShieldCheck, Clock, User, FileText, Database } from 'lucide-react';

export const AuditLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchLogs = async () => {
      setIsLoading(true);
      try {
        const data = await api.get<AuditLog[]>('/audit/logs');
        setLogs(data);
      } catch (err) {
        console.error('Failed to load audit logs', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchLogs();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight font-display flex items-center gap-2">
          <ShieldCheck className="w-7 h-7 text-brand-600" />
          Security & Audit Governance Trail
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Immutable historical log capturing marks approvals, attendance corrections, and administrative modifications
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-slate-900 text-white font-bold uppercase tracking-wider">
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Actor</th>
                <th className="py-3 px-4">Entity</th>
                <th className="py-3 px-4">Audit Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {logs.map(l => (
                <tr key={l.id} className="hover:bg-slate-50/70">
                  <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                    {formatIndianDateTime(l.created_at)}
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-extrabold text-brand-700 bg-brand-50 border border-brand-200 px-2 py-0.5 rounded text-[11px]">
                      {l.action}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-semibold text-slate-900">
                    {l.user_name || 'System Admin'}
                  </td>
                  <td className="py-3 px-4 text-slate-600 font-mono text-[11px]">
                    {l.entity_type}
                  </td>
                  <td className="py-3 px-4 text-slate-600 max-w-xs truncate">
                    {l.reason ? (
                      <span className="italic">"{l.reason}"</span>
                    ) : (
                      <span className="text-slate-400">Standard audited execution</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
