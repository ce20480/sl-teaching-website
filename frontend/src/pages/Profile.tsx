import { Settings, Award, History, LogOut, ArrowRight } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAccount } from "wagmi";
import { AchievementDisplay } from "@/components/AchievementDisplay";
import { ExperienceDisplay } from "@/components/ExperienceDisplay";
import { WalletConnect } from "@/components/WalletConnect";

const Profile = () => {
  const { isConnected } = useAccount();

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-6">Your ASL Profile</h1>

      <div className="mb-8">
        <WalletConnect />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* XP Display */}
        <div>
          <h2 className="text-xl font-semibold mb-4">Experience Points</h2>
          <ExperienceDisplay />
        </div>

        {/* Achievements */}
        <div>
          <h2 className="text-xl font-semibold mb-4">Your Achievements</h2>
          <AchievementDisplay />
        </div>
      </div>

      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Profile</h1>
          <Settings className="h-6 w-6 text-muted-foreground cursor-pointer" />
        </div>

        <div className="flex flex-col items-center space-y-4">
          <Avatar className="h-24 w-24">
            <AvatarImage src="https://github.com/shadcn.png" />
            <AvatarFallback>JD</AvatarFallback>
          </Avatar>
          <div className="text-center">
            <h2 className="text-2xl font-semibold">John Doe</h2>
            <p className="text-muted-foreground">Member since March 2024</p>
          </div>
          <div className="flex gap-2">
            <Badge variant="secondary">Level 5</Badge>
            <Badge variant="secondary">1250 XP</Badge>
          </div>
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Award className="h-5 w-5 text-primary" />
              <CardTitle>Achievements</CardTitle>
            </div>
            <CardDescription>Your on-chain accomplishments</CardDescription>
          </CardHeader>
          <CardContent>
            {!isConnected ? (
              <div className="text-center py-4 text-muted-foreground">
                Please connect your wallet to view your achievements
              </div>
            ) : (
              <AchievementDisplay />
            )}
          </CardContent>
        </Card>

        <div className="grid gap-4">
          <Card className="cursor-pointer hover:bg-accent/50 transition-colors">
            <CardContent className="flex items-center justify-between p-6">
              <div className="flex items-center gap-3">
                <History className="h-5 w-5 text-primary" />
                <span>Learning History</span>
              </div>
              <ArrowRight className="h-5 w-5 text-muted-foreground" />
            </CardContent>
          </Card>

          <Card className="cursor-pointer hover:bg-destructive/10 transition-colors">
            <CardContent className="flex items-center justify-between p-6">
              <div className="flex items-center gap-3">
                <LogOut className="h-5 w-5 text-destructive" />
                <span className="text-destructive">Sign Out</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Profile;
