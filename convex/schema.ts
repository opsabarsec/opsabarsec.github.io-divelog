// convex/schema.ts
import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

const schema = defineSchema({
<<<<<<< HEAD
  certifications: defineTable({
    user_id: v.string(),
    name: v.string(),              // e.g., "Open Water Diver", "Advanced Open Water"
    agency: v.string(),            // e.g., "PADI", "SSI", "CMAS"
    certification_date: v.number(), // Unix timestamp in milliseconds
    certification_number: v.optional(v.string()),
    instructor_name: v.optional(v.string()),
    dive_center: v.optional(v.string()),
    created_at: v.number(),
  }).index("by_user", ["user_id"]),
=======
  checklists: defineTable({
    name: v.string(),
    link: v.string(),
  }),
>>>>>>> c8fefac (checklists)

  dives: defineTable({
    user_id: v.string(),
    dive_number: v.number(), // now required
    dive_date: v.number(),
    location: v.string(),

    latitude: v.optional(v.number()),
    longitude: v.optional(v.number()),
    // NEW: OpenStreetMap link stored by the backend
    osm_link: v.optional(v.string()),

    site: v.optional(v.string()),
    duration: v.number(),
    max_depth: v.number(),
    temperature: v.optional(v.number()),
    visibility: v.optional(v.number()),
    weather: v.optional(v.string()),
    suit_thickness: v.optional(v.number()),
    lead_weights: v.optional(v.number()),

    // REQUIRED fields (matched to Python + upsertDive)
    club_name: v.string(),
    instructor_name: v.string(),
    photo_storage_ids: v.array(v.string()),
    club_website: v.optional(v.string()),
    notes: v.optional(v.string()),

    // Flags from Convex mutation (PascalCase preserved)
    Buddy_check: v.boolean(),
    Briefed: v.boolean(),

    // Server–managed timestamps
    logged_at: v.number(),
    updated_at: v.number(),
  })
    .index("by_dive_number", ["user_id", "dive_number"]),
});

export default schema;