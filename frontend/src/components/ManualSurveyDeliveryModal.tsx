"use client";

import { useState } from 'react';
import { X, Users, Send, AlertTriangle } from 'lucide-react';

interface Recipient {
  name: string;
  email: string;
}

interface PreviewResponse {
  requires_confirmation: boolean;
  message: string;
  recipient_count: number;
  recipients: Recipient[];
  note: string;
}

interface SuccessResponse {
  success: boolean;
  message: string;
  recipient_count: number;
  triggered_by: string;
}

interface ManualSurveyDeliveryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export default function ManualSurveyDeliveryModal({
  isOpen,
  onClose,
  onSuccess
}: ManualSurveyDeliveryModalProps) {
  const [step, setStep] = useState<'preview' | 'confirm' | 'success' | 'error'>('preview');
  const [loading, setLoading] = useState(false);
  const [previewData, setPreviewData] = useState<PreviewResponse | null>(null);
  const [successData, setSuccessData] = useState<SuccessResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchPreview = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/survey-schedule/manual-delivery', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ confirmed: false })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch preview');
      }

      const data = await response.json();
      setPreviewData(data);
      setStep('confirm');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setStep('error');
    } finally {
      setLoading(false);
    }
  };

  const confirmDelivery = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/survey-schedule/manual-delivery', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ confirmed: true })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to send surveys');
      }

      const data = await response.json();
      setSuccessData(data);
      setStep('success');
      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setStep('error');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setStep('preview');
    setPreviewData(null);
    setSuccessData(null);
    setError(null);
    onClose();
  };

  const handleOpen = () => {
    if (step === 'preview') {
      fetchPreview();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {step === 'preview' && 'Send Survey Now'}
            {step === 'confirm' && 'Confirm Survey Delivery'}
            {step === 'success' && 'Survey Sent Successfully'}
            {step === 'error' && 'Error'}
          </h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {/* Preview Step */}
          {step === 'preview' && (
            <div className="space-y-4">
              <div className="flex items-start space-x-3 p-4 bg-blue-50 rounded-lg">
                <Users className="w-5 h-5 text-blue-600 mt-0.5" />
                <div>
                  <p className="text-sm text-gray-700">
                    This will immediately send burnout check-in surveys to all opted-in team members via Slack DM.
                  </p>
                </div>
              </div>
              <p className="text-sm text-gray-600">
                Click "Preview Recipients" to see who will receive the survey before sending.
              </p>
            </div>
          )}

          {/* Confirm Step */}
          {step === 'confirm' && previewData && (
            <div className="space-y-4">
              <div className="flex items-start space-x-3 p-4 bg-yellow-50 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5" />
                <div>
                  <p className="font-medium text-gray-900">
                    {previewData.message}
                  </p>
                  <p className="text-sm text-gray-600 mt-1">
                    This action cannot be undone.
                  </p>
                </div>
              </div>

              <div>
                <h3 className="font-medium text-gray-900 mb-3">
                  Recipients ({previewData.recipient_count})
                </h3>
                <div className="bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
                  <ul className="space-y-2">
                    {previewData.recipients.map((recipient, index) => (
                      <li key={index} className="flex items-center space-x-3 text-sm">
                        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-medium">
                          {recipient.name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{recipient.name}</p>
                          <p className="text-gray-500">{recipient.email}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Success Step */}
          {step === 'success' && successData && (
            <div className="space-y-4">
              <div className="flex items-center justify-center p-8">
                <div className="text-center">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Send className="w-8 h-8 text-green-600" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {successData.message}
                  </h3>
                  <p className="text-sm text-gray-600">
                    Surveys have been sent to {successData.recipient_count} team members.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Error Step */}
          {step === 'error' && error && (
            <div className="space-y-4">
              <div className="flex items-start space-x-3 p-4 bg-red-50 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5" />
                <div>
                  <p className="font-medium text-gray-900">Failed to send surveys</p>
                  <p className="text-sm text-gray-600 mt-1">{error}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 bg-gray-50">
          {step === 'preview' && (
            <>
              <button
                onClick={handleClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleOpen}
                disabled={loading}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Loading...' : 'Preview Recipients'}
              </button>
            </>
          )}

          {step === 'confirm' && (
            <>
              <button
                onClick={handleClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelivery}
                disabled={loading}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                <Send className="w-4 h-4" />
                <span>{loading ? 'Sending...' : 'Confirm & Send'}</span>
              </button>
            </>
          )}

          {(step === 'success' || step === 'error') && (
            <button
              onClick={handleClose}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
