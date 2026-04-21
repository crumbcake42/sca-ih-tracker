import { createFileRoute } from "@tanstack/react-router";

const IndexComponent: React.FC = () => {
  return (
    <div>
      Welcome to SCA IH Tracker! Please <a href="/login">log in</a> to continue.
    </div>
  );
};

export const Route = createFileRoute("/")({
  component: IndexComponent,
});
