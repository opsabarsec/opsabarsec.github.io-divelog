// convex/checklists.ts
import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const createChecklist = mutation({
  args: {
    name: v.string(),
    link: v.string(),
  },
  handler: async (ctx, args) => {
    const id = await ctx.db.insert("checklists", {
      name: args.name,
      link: args.link,
    });
    return { id };
  },
});

export const getAllChecklists = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db.query("checklists").collect();
  },
});

export const getChecklistById = query({
  args: { id: v.id("checklists") },
  handler: async (ctx, args) => {
    return await ctx.db.get(args.id);
  },
});

export const updateChecklist = mutation({
  args: {
    id: v.id("checklists"),
    name: v.optional(v.string()),
    link: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const { id, ...fields } = args;
    const existing = await ctx.db.get(id);
    if (!existing) {
      throw new Error(`Checklist with id '${id}' not found`);
    }
    await ctx.db.patch(id, fields);
    return { id };
  },
});

export const deleteChecklist = mutation({
  args: { id: v.id("checklists") },
  handler: async (ctx, args) => {
    const existing = await ctx.db.get(args.id);
    if (!existing) {
      throw new Error(`Checklist with id '${args.id}' not found`);
    }
    await ctx.db.delete(args.id);
    return { id: args.id };
  },
});
