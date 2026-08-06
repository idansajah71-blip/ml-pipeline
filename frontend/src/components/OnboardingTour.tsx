'use client';

import { useState, useEffect } from 'react';
import { X, ArrowRight, Lightbulb } from 'lucide-react';

interface TourStep {
  target: string;
  title: string;
  content: string;
}

const TOUR_STEPS: TourStep[] = [
  {
    target: '[data-tour="wizard"]',
    title: 'Mulai di sini!',
    content: 'Training Wizard memandu Anda melatih model tanpa perlu pengetahuan teknis.',
  },
  {
    target: '[data-tour="datasets"]',
    title: 'Dataset Anda',
    content: 'Unggah dan kelola data. Mendukung CSV, Excel, JSON, dan Google Sheets.',
  },
  {
    target: '[data-tour="models"]',
    title: 'Model ML',
    content: 'Lihat semua model yang sudah dilatih, deploy, atau bandingkan performa.',
  },
  {
    target: '[data-tour="experiments"]',
    title: 'Eksperimen',
    content: 'Bandangkan hasil training dari berbagai algoritma dan parameter.',
  },
];

const STORAGE_KEY = 'ml-pipeline-onboarding-done';

export default function OnboardingTour() {
  const [currentStep, setCurrentStep] = useState(0);
  const [visible, setVisible] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  useEffect(() => {
    const done = localStorage.getItem(STORAGE_KEY);
    if (!done) {
      setTimeout(() => setVisible(true), 1000);
    }

    const handleRestart = () => {
      localStorage.removeItem(STORAGE_KEY);
      setCurrentStep(0);
      setVisible(true);
    };
    window.addEventListener('restart-onboarding', handleRestart);
    return () => window.removeEventListener('restart-onboarding', handleRestart);
  }, []);

  useEffect(() => {
    if (!visible) return;
    const step = TOUR_STEPS[currentStep];
    if (!step) return;

    const el = document.querySelector(step.target);
    if (el) {
      const rect = el.getBoundingClientRect();
      setPosition({
        top: rect.bottom + 8,
        left: Math.min(rect.left, window.innerWidth - 320),
      });
    }
  }, [currentStep, visible]);

  const handleNext = () => {
    if (currentStep < TOUR_STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      finish();
    }
  };

  const finish = () => {
    localStorage.setItem(STORAGE_KEY, 'true');
    setVisible(false);
  };

  if (!visible || currentStep >= TOUR_STEPS.length) return null;

  const step = TOUR_STEPS[currentStep];

  return (
    <div className="fixed inset-0 z-[100]">
      <div className="fixed inset-0 bg-black/30" onClick={finish} />
      <div
        className="fixed z-[101] w-72 rounded-xl bg-white p-5 shadow-2xl"
        style={{ top: position.top, left: position.left }}
      >
        <div className="mb-3 flex items-center gap-2">
          <Lightbulb className="h-5 w-5 text-yellow-500" />
          <span className="text-xs font-medium text-gray-500">Langkah {currentStep + 1}/{TOUR_STEPS.length}</span>
          <button onClick={finish} className="ml-auto text-gray-400 hover:text-gray-600">
            <X className="h-4 w-4" />
          </button>
        </div>
        <h4 className="mb-2 font-semibold text-gray-900">{step.title}</h4>
        <p className="mb-4 text-sm text-gray-600">{step.content}</p>
        <div className="flex items-center justify-between">
          <div className="flex gap-1">
            {TOUR_STEPS.map((_, i) => (
              <div key={i} className={`h-1.5 w-1.5 rounded-full ${i === currentStep ? 'bg-primary-600' : 'bg-gray-300'}`} />
            ))}
          </div>
          <button
            onClick={handleNext}
            className="flex items-center gap-1 rounded-lg bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700"
          >
            {currentStep === TOUR_STEPS.length - 1 ? 'Selesai' : 'Selanjutnya'}
            <ArrowRight className="h-3 w-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
