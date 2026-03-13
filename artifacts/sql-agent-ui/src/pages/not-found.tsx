import { Link } from "wouter";
import { AlertCircle, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui";

export default function NotFound() {
  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-center bg-background text-foreground relative overflow-hidden">
      <div 
        className="absolute inset-0 z-0 opacity-10 pointer-events-none"
        style={{ backgroundImage: `url(${import.meta.env.BASE_URL}images/abstract-bg.png)`, backgroundSize: 'cover' }}
      />
      
      <div className="z-10 flex flex-col items-center text-center p-8 bg-card/80 backdrop-blur-md border border-border rounded-2xl shadow-2xl max-w-md w-full mx-4">
        <div className="w-16 h-16 rounded-full bg-destructive/10 flex items-center justify-center mb-6">
          <AlertCircle className="h-8 w-8 text-destructive" />
        </div>
        
        <h1 className="text-4xl font-bold mb-2">404</h1>
        <h2 className="text-xl font-semibold text-slate-300 mb-4">Page Not Found</h2>
        
        <p className="text-muted-foreground mb-8">
          The route you requested doesn't exist in the SQL Agent UI.
        </p>
        
        <Link href="/" className="w-full">
          <Button className="w-full gap-2">
            <ArrowLeft className="w-4 h-4" />
            Back to Query Tester
          </Button>
        </Link>
      </div>
    </div>
  );
}
