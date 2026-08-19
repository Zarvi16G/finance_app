/**
 * Shared card container used across dashboard
sections for a consistent template look.
 */
import React from "react";
import { Card } from "../ui/card";

interface MyAppProps {
  children: React.ReactNode;
  className?: string;
}
const CardBox: React.FC<MyAppProps> = ({ children, className }) => {
  return (
    <Card className={`card no-inset no-ring ${className} shadow-sm border border-border rounded-none w-full`}>
      {children}
    </Card>
  );

};
export default CardBox;
