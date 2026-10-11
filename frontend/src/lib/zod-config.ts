import { z } from "zod";

// Zod 4 tests whether it can use eval (new Function) to build faster validators. Our CSP forbids
// eval, so that test only produces a browser warning. jitless skips the test; results are identical.
z.config({ jitless: true });
