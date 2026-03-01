'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/components/ui/use-toast';
import { apiPost } from '@/lib/api';
import { SetupStatus } from '@/lib/types';

type SetupStep = 'admin' | 'email' | 'google' | 'general';

const STEPS: Array<{ id: SetupStep; title: string; optional?: boolean }> = [
  { id: 'admin', title: 'Admin Account' },
  { id: 'email', title: 'Email Settings', optional: true },
  { id: 'google', title: 'Google Integrations', optional: true },
  { id: 'general', title: 'General Settings' },
];

export default function SetupPage() {
  const router = useRouter();
  const { toast } = useToast();
  
  const [currentStep, setCurrentStep] = useState<SetupStep>('admin');
  const [loading, setLoading] = useState(false);
  const [completedSteps, setCompletedSteps] = useState<SetupStep[]>([]);
  
  const [adminData, setAdminData] = useState({
    email: '',
    password: '',
    name: ''
  });
  
  const [emailData, setEmailData] = useState({
    smtpHost: '',
    smtpPort: '587',
    smtpUser: '',
    smtpPassword: '',
    senderEmail: ''
  });
  
  const [googleData, setGoogleData] = useState({
    clientId: '',
    clientSecret: '',
    measurementId: ''
  });
  
  const [generalData, setGeneralData] = useState({
    appUrl: '',
    maxConcurrentCrawls: '5'
  });

  const handleSubmit = async () => {
    try {
      setLoading(true);
      
      const allData = {
        ...adminData,
        ...emailData,
        ...googleData,
        ...generalData
      };
      
      await apiPost('/api/setup/complete', {
        admin_email: adminData.email,
        admin_password: adminData.password,
        admin_name: adminData.name,
        settings: allData
      });
      
      router.push('/auth/login');
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Setup failed',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const getStepComponent = () => {
    switch (currentStep) {
      case 'admin':
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="email">Admin Email</Label>
              <Input
                id="email"
                type="email"
                value={adminData.email}
                onChange={(e) => setAdminData({...adminData, email: e.target.value})}
              />
            </div>
            <div>
              <Label htmlFor="password">Password (min. 8 characters)</Label>
              <Input
                id="password"
                type="password"
                value={adminData.password}
                onChange={(e) => setAdminData({...adminData, password: e.target.value})}
              />
            </div>
            <div>
              <Label htmlFor="name">Admin Name</Label>
              <Input
                id="name"
                value={adminData.name}
                onChange={(e) => setAdminData({...adminData, name: e.target.value})}
              />
            </div>
          </div>
        );
      
      case 'email':
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="smtpHost">SMTP Host</Label>
              <Input
                id="smtpHost"
                value={emailData.smtpHost}
                onChange={(e) => setEmailData({...emailData, smtpHost: e.target.value})}
              />
            </div>
            <div>
              <Label htmlFor="smtpPort">SMTP Port</Label>
              <Input
                id="smtpPort"
                type="number"
                value={emailData.smtpPort}
                onChange={(e) => setEmailData({...emailData, smtpPort: e.target.value})}
              />
            </div>
            <div>
              <Label htmlFor="smtpUser">SMTP Username</Label>
              <Input
                id="smtpUser"
                value={emailData.smtpUser}
                onChange={(e) => setEmailData({...emailData, smtpUser: e.target.value})}
              />
            </div>
            <div>
              <Label htmlFor="smtpPassword">SMTP Password</Label>
              <Input
                id="smtpPassword"
                type="password"
                value={emailData.smtpPassword}
                onChange={(e) => setEmailData({...emailData, smtpPassword: e.target.value})}
              />
            </div>
            <div>
              <Label htmlFor="senderEmail">Sender Email</Label>
              <Input
                id="senderEmail"
                type="email"
                value={emailData.senderEmail}
                onChange={(e) => setEmailData({...emailData, senderEmail: e.target.value})}
              />
            </div>
          </div>
        );
      
      case 'google':
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="clientId">Google Search Console Client ID</Label>
              <Input
                id="clientId"
                value={googleData.clientId}
                onChange={(e) => setGoogleData({...googleData, clientId: e.target.value})}
              />
            </div>
            <div>
              <Label htmlFor="clientSecret">Google Search Console Client Secret</Label>
              <Input
                id="clientSecret"
                type="password"
                value={googleData.clientSecret}
                onChange={(e) => setGoogleData({...googleData, clientSecret: e.target.value})}
              />
            </div>
            <div>
              <Label htmlFor="measurementId">Google Analytics Measurement ID</Label>
              <Input
                id="measurementId"
                value={googleData.measurementId}
                onChange={(e) => setGoogleData({...googleData, measurementId: e.target.value})}
              />
            </div>
          </div>
        );
      
      case 'general':
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="appUrl">Application URL</Label>
              <Input
                id="appUrl"
                value={generalData.appUrl}
                onChange={(e) => setGeneralData({...generalData, appUrl: e.target.value})}
                placeholder="http://example.com:8080"
              />
            </div>
            <div>
              <Label htmlFor="maxConcurrentCrawls">Max Concurrent Crawls</Label>
              <Input
                id="maxConcurrentCrawls"
                type="number"
                min="1"
                value={generalData.maxConcurrentCrawls}
                onChange={(e) => setGeneralData({...generalData, maxConcurrentCrawls: e.target.value})}
              />
            </div>
          </div>
        );
    }
  };

  const progressValue = ((STEPS.findIndex(s => s.id === currentStep) + 1) / STEPS.length) * 100;
  const currentStepIndex = STEPS.findIndex(s => s.id === currentStep);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow">
        <h1 className="text-2xl font-bold text-center">WebCrawler Pro Setup</h1>
        
        <div className="space-y-2">
          <div className="flex justify-between">
            {STEPS.map((step) => (
              <div key={step.id} className="text-center">
                <div className={`w-8 h-8 mx-auto rounded-full flex items-center justify-center ${completedSteps.includes(step.id) ? 'bg-green-500 text-white' : currentStep === step.id ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}>
                  {STEPS.findIndex(s => s.id === step.id) + 1}
                </div>
                <div className="text-xs mt-1">{step.title}</div>
              </div>
            ))}
          </div>
          <Progress value={progressValue} className="h-2" />
        </div>
        
        <h2 className="text-lg font-medium">{STEPS[currentStepIndex].title}</h2>
        
        {getStepComponent()}
        
        <div className="flex justify-between pt-4">
          {currentStepIndex > 0 ? (
            <Button
              variant="outline"
              onClick={() => setCurrentStep(STEPS[currentStepIndex - 1].id as SetupStep)}
            >
              Back
            </Button>
          ) : (
            <div />
          )}
          
          <div className="space-x-2">
            {STEPS[currentStepIndex].optional && (
              <Button
                variant="ghost"
                onClick={() => {
                  setCompletedSteps([...completedSteps, currentStep]);
                  setCurrentStep(STEPS[currentStepIndex + 1].id as SetupStep);
                }}
              >
                Skip
              </Button>
            )}
            
            {currentStepIndex < STEPS.length - 1 ? (
              <Button
                onClick={() => {
                  setCompletedSteps([...completedSteps, currentStep]);
                  setCurrentStep(STEPS[currentStepIndex + 1].id as SetupStep);
                }}
              >
                Next
              </Button>
            ) : (
              <Button onClick={handleSubmit} disabled={loading}>
                {loading ? 'Completing...' : 'Complete Setup'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
