// convex/dives.ts
import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const upsertDive = mutation({
  args: {
    user_id: v.string(),
    dive_number: v.number(),
    dive_date: v.number(),
    location: v.string(),

    latitude: v.optional(v.number()),
    longitude: v.optional(v.number()),
    // NEW: Accept osm_link from the API layer
    osm_link: v.optional(v.string()),

    site: v.optional(v.string()),
    duration: v.number(),
    max_depth: v.number(),
    temperature: v.optional(v.number()),
    visibility: v.optional(v.number()),
    weather: v.optional(v.string()),
    suit_thickness: v.optional(v.number()),
    lead_weights: v.optional(v.number()),

    // REQUIRED
    club_name: v.string(),
    instructor_name: v.string(),
    photo_storage_ids: v.array(v.string()),
    club_website: v.optional(v.string()),
    notes: v.optional(v.string()),

    // Dive mode
    mode: v.optional(v.string()),

    // Flags
    Buddy_check: v.boolean(),
    Briefed: v.boolean(),
  },
  handler: async (ctx, args) => {
    const { user_id, dive_number } = args;
    const now = Date.now();

    const existing = await ctx.db
      .query("dives")
      .withIndex("by_dive_number", q =>
        q.eq("user_id", user_id).eq("dive_number", dive_number)
      )
      .unique();

    if (existing) {
      await ctx.db.patch(existing._id, {
        ...args,
        updated_at: now,
      });
      return { id: existing._id, action: "updated" };
    }

    const id = await ctx.db.insert("dives", {
      ...args,
      logged_at: now,
      updated_at: now,
    });
    return { id, action: "inserted" };
  },
});

export const getDiveById = query({
  args: { id: v.id("dives") },
  handler: async (ctx, args) => {
    return await ctx.db.get(args.id);
  },
});

export const getAllDives = query({
  args: { user_id: v.string() },
  handler: async (ctx, args) => {
    const dives = await ctx.db
      .query("dives")
      .withIndex("by_dive_number", (q) => q.eq("user_id", args.user_id))
      .collect();
    // Sort by dive_date descending (most recent first)
    return dives.sort((a, b) => b.dive_date - a.dive_date);
  },
});

export const getLatestDive = query({
  args: { user_id: v.string() },
  handler: async (ctx, args) => {
    const dives = await ctx.db
      .query("dives")
      .withIndex("by_dive_number", (q) => q.eq("user_id", args.user_id))
      .collect();
    if (dives.length === 0) return null;
    // Return the dive with the most recent dive_date
    return dives.sort((a, b) => b.dive_date - a.dive_date)[0];
  },
});

export const getLatestFreedive = query({
  args: { user_id: v.string() },
  handler: async (ctx, args) => {
    const dives = await ctx.db
      .query("dives")
      .withIndex("by_dive_number", (q) => q.eq("user_id", args.user_id))
      .collect();
    const freedives = dives.filter(d => d.mode === "freediving");
    if (freedives.length === 0) return null;
    return freedives.sort((a, b) => b.dive_date - a.dive_date)[0];
  },
});

export const deleteDive = mutation({
  args: { id: v.id("dives") },
  handler: async (ctx, args) => {
    const existing = await ctx.db.get(args.id);
    if (!existing) {
      throw new Error(`Dive with id ${args.id} not found`);
    }
    await ctx.db.delete(args.id);
    return { success: true, deleted_id: args.id };
  },
});
