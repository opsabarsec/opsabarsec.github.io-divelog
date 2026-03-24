// convex/certifications.ts
import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const addCertification = mutation({
  args: {
    user_id: v.string(),
    name: v.string(),
    agency: v.string(),
    certification_date: v.number(),
    certification_number: v.optional(v.string()),
    instructor_name: v.optional(v.string()),
    dive_center: v.optional(v.string()),
    photo_url: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const id = await ctx.db.insert("certifications", {
      ...args,
      created_at: Date.now(),
    });
    return { id, action: "inserted" };
  },
});

export const getAllCertifications = query({
  args: { user_id: v.string() },
  handler: async (ctx, args) => {
    const certs = await ctx.db
      .query("certifications")
      .withIndex("by_user", (q) => q.eq("user_id", args.user_id))
      .collect();
    // Sort by certification_date descending (most recent first)
    return certs.sort((a, b) => b.certification_date - a.certification_date);
  },
});

export const deleteCertification = mutation({
  args: { id: v.id("certifications") },
  handler: async (ctx, args) => {
    const existing = await ctx.db.get(args.id);
    if (!existing) {
      throw new Error(`Certification with id ${args.id} not found`);
    }
    await ctx.db.delete(args.id);
    return { success: true, deleted_id: args.id };
  },
});
