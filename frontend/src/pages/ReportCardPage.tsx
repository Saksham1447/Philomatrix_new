import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { ReportCardData, Examination, Student } from '../types';
import {
  FileText,
  Download,
  Printer,
  GraduationCap,
  CheckCircle2,
  AlertTriangle,
  Award,
  CalendarCheck
} from 'lucide-react';

export const ReportCardPage: React.FC = () => {
  const { user, activeRole, activeChild } = useAuth();
  const [examinations, setExaminations] = useState<Examination[]>([]);
  const [selectedExamId, setSelectedExamId] = useState<string>('');
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState<string>('');
  const [reportData, setReportData] = useState<ReportCardData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const initData = async () => {
      try {
        const exams = await api.get<Examination[]>('/examinations');
        setExaminations(exams);
        if (exams.length > 0) {
          setSelectedExamId(exams[0].id);
        }

        if (activeRole === 'PRINCIPAL' || activeRole === 'FACULTY' || activeRole === 'OFFICE_STAFF') {
          const stList = await api.get<Student[]>('/students');
          setStudents(stList);
          if (stList.length > 0) {
            setSelectedStudentId(stList[0].id);
          }
        } else if (activeRole === 'STUDENT' && user?.student_id) {
          setSelectedStudentId(user.student_id);
        } else if (activeRole === 'PARENT' && activeChild) {
          setSelectedStudentId(activeChild.id);
        }
      } catch (err: any) {
        console.error('Failed to init report card metadata', err);
      }
    };
    initData();
  }, [activeRole, activeChild, user]);

  useEffect(() => {
    if (selectedExamId && selectedStudentId) {
      loadReportCard(selectedExamId, selectedStudentId);
    }
  }, [selectedExamId, selectedStudentId]);

  const loadReportCard = async (examId: string, studentId: string) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await api.get<ReportCardData>(
        `/reports/report-card/${examId}/student/${studentId}`
      );
      setReportData(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Results for this examination have not been published yet');
      setReportData(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!selectedExamId || !selectedStudentId) return;
    setIsDownloading(true);
    try {
      const filename = `ReportCard_${reportData?.admission_number || 'Student'}_${selectedExamId.slice(0, 8)}.pdf`;
      await api.downloadPdf(
        `/reports/report-card/${selectedExamId}/student/${selectedStudentId}/pdf`,
        filename
      );
    } catch (err: any) {
      alert(err.message || 'Failed to download PDF');
    } finally {
      setIsDownloading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-6">
      {/* Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 print:hidden">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight font-display flex items-center gap-2">
            <FileText className="w-7 h-7 text-brand-600" />
            Official Academic Report Card
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Certified Grade Sheet with Theory, Practical Breakdown, and Term Attendance Summary
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handlePrint}
            className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <Printer className="w-4 h-4" /> Print
          </button>
          <button
            onClick={handleDownloadPdf}
            disabled={isDownloading || !reportData}
            className="px-4 py-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-md shadow-brand-500/20 transition-all flex items-center gap-1.5 cursor-pointer"
          >
            <Download className="w-4 h-4" />
            <span>{isDownloading ? 'Generating PDF...' : 'Download Official PDF'}</span>
          </button>
        </div>
      </div>

      {/* Selectors for Principal/Staff */}
      {(activeRole === 'PRINCIPAL' || activeRole === 'FACULTY' || activeRole === 'OFFICE_STAFF') && (
        <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-xs flex flex-wrap gap-4 items-center print:hidden">
          <div>
            <label className="block text-[11px] font-bold text-slate-400 uppercase">
              Select Examination
            </label>
            <select
              value={selectedExamId}
              onChange={e => setSelectedExamId(e.target.value)}
              className="mt-1 px-3 py-1.5 text-xs font-semibold bg-slate-50 border border-slate-200 rounded-lg"
            >
              {examinations.map(ex => (
                <option key={ex.id} value={ex.id}>
                  {ex.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-bold text-slate-400 uppercase">
              Select Student
            </label>
            <select
              value={selectedStudentId}
              onChange={e => setSelectedStudentId(e.target.value)}
              className="mt-1 px-3 py-1.5 text-xs font-semibold bg-slate-50 border border-slate-200 rounded-lg"
            >
              {students.map(st => (
                <option key={st.id} value={st.id}>
                  {st.full_name} ({st.admission_number} - Div {st.division_name})
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {errorMsg ? (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-8 text-center text-amber-800">
          <AlertTriangle className="w-8 h-8 text-amber-600 mx-auto mb-2" />
          <h3 className="text-base font-bold font-display">Report Card Not Available</h3>
          <p className="text-xs text-amber-700 mt-1">{errorMsg}</p>
        </div>
      ) : reportData ? (
        /* Printable Report Card Document */
        <div className="bg-white rounded-2xl border border-slate-300 shadow-xl p-8 sm:p-12 max-w-4xl mx-auto print:p-0 print:border-none print:shadow-none">
          {/* Institution Header */}
          <div className="text-center pb-6 border-b-2 border-slate-900">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-brand-700 text-white mb-2">
              <GraduationCap className="w-7 h-7" />
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-display tracking-tight uppercase">
              {reportData.institution_name}
            </h2>
            <p className="text-xs text-slate-600 mt-0.5">
              {reportData.institution_address} • Code: {reportData.institution_code}
            </p>
            <div className="inline-block mt-3 px-4 py-1 rounded-full bg-slate-100 text-slate-800 font-bold text-xs uppercase tracking-wider border border-slate-300">
              Official Progress Report — {reportData.examination_name}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Academic Year {reportData.academic_year}</p>
          </div>

          {/* Student Demographics Table */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-6 text-xs border-b border-slate-200 bg-slate-50/50 px-4 my-4 rounded-xl">
            <div>
              <p className="text-slate-400 font-semibold uppercase">Student Name</p>
              <p className="font-bold text-slate-900 text-sm mt-0.5">{reportData.student_name}</p>
            </div>
            <div>
              <p className="text-slate-400 font-semibold uppercase">Admission No</p>
              <p className="font-bold text-slate-900 text-sm mt-0.5">{reportData.admission_number}</p>
            </div>
            <div>
              <p className="text-slate-400 font-semibold uppercase">Class & Division</p>
              <p className="font-bold text-slate-900 text-sm mt-0.5">
                {reportData.class_name} - {reportData.division_name} ({reportData.stream})
              </p>
            </div>
            <div>
              <p className="text-slate-400 font-semibold uppercase">Term Attendance</p>
              <p className="font-bold text-emerald-700 text-sm mt-0.5">
                {reportData.attendance_percentage}% ({reportData.total_attended_lectures}/{reportData.total_conducted_lectures} Lectures)
              </p>
            </div>
          </div>

          {/* Scores Matrix Table */}
          <div className="overflow-x-auto my-6">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-brand-900 text-white font-bold uppercase tracking-wider">
                  <th className="py-2.5 px-3">Subject Code</th>
                  <th className="py-2.5 px-3">Subject Name</th>
                  <th className="py-2.5 px-3 text-center">Theory (Max)</th>
                  <th className="py-2.5 px-3 text-center">Practical (Max)</th>
                  <th className="py-2.5 px-3 text-center">Total Max</th>
                  <th className="py-2.5 px-3 text-center">Total Obtained</th>
                  <th className="py-2.5 px-3 text-center">%</th>
                  <th className="py-2.5 px-3 text-center">Grade</th>
                  <th className="py-2.5 px-3 text-center">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 border-b border-slate-200">
                {reportData.subjects.map((s, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50">
                    <td className="py-2.5 px-3 font-semibold text-slate-600">{s.subject_code}</td>
                    <td className="py-2.5 px-3 font-bold text-slate-900">{s.subject_name}</td>
                    <td className="py-2.5 px-3 text-center">
                      {s.theory_obtained ?? '-'} / {s.theory_max}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {s.practical_obtained ?? '-'} / {s.practical_max}
                    </td>
                    <td className="py-2.5 px-3 text-center font-semibold">{s.total_max}</td>
                    <td className="py-2.5 px-3 text-center font-extrabold text-slate-900">
                      {s.total_obtained ?? '-'}
                    </td>
                    <td className="py-2.5 px-3 text-center font-bold text-slate-700">{s.percentage}%</td>
                    <td className="py-2.5 px-3 text-center font-bold text-brand-700">{s.grade}</td>
                    <td className="py-2.5 px-3 text-center">
                      <span
                        className={`font-extrabold ${
                          s.status === 'PASS' ? 'text-emerald-700' : 'text-rose-700'
                        }`}
                      >
                        {s.status}
                      </span>
                    </td>
                  </tr>
                ))}

                {/* Grand Total Footer Row */}
                <tr className="bg-slate-100 font-extrabold text-slate-900 border-t-2 border-slate-900">
                  <td colSpan={2} className="py-3 px-3 uppercase tracking-wider">
                    Grand Aggregate Total
                  </td>
                  <td className="py-3 px-3 text-center">-</td>
                  <td className="py-3 px-3 text-center">-</td>
                  <td className="py-3 px-3 text-center">{reportData.grand_total_max}</td>
                  <td className="py-3 px-3 text-center text-brand-900 text-sm">
                    {reportData.grand_total_obtained}
                  </td>
                  <td className="py-3 px-3 text-center text-sm">{reportData.overall_percentage}%</td>
                  <td className="py-3 px-3 text-center text-brand-700">{reportData.overall_grade}</td>
                  <td className="py-3 px-3 text-center text-emerald-800">
                    {reportData.final_result}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Remarks & Authorizations */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-6 border-t border-slate-200 text-xs">
            <div>
              <p className="font-bold text-slate-800 uppercase tracking-wider">Teacher Remarks:</p>
              <p className="text-slate-600 mt-1 italic">"{reportData.teacher_remarks}"</p>
              <div className="mt-8 pt-4 border-t border-slate-300 w-48">
                <p className="font-semibold text-slate-800">Class Teacher Signature</p>
              </div>
            </div>

            <div className="sm:text-right flex flex-col justify-between">
              <div>
                <p className="font-bold text-slate-800 uppercase tracking-wider">Principal Remarks:</p>
                <p className="text-slate-600 mt-1 italic">"{reportData.principal_remarks}"</p>
              </div>
              <div className="mt-8 pt-4 border-t border-slate-300 w-48 sm:ml-auto">
                <p className="font-semibold text-slate-800">Principal Seal & Signature</p>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
